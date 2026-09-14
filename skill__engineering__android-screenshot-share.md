---
name: android-screenshot-share
description: Android 页面截图分享模式 — 隐藏指定控件后截图，通过分享弹窗发送到微信/QQ/保存相册
triggers:
  - Android 页面截图分享
  - 截图不含某些控件（返回键、分享按钮等）
  - CommonShareDialog 图片分享
---

# Android 页面截图分享

## 核心流程

```
点击分享按钮
  → 隐藏不想出现的控件（INVISIBLE，保留占位）
  → rootView.post { }  ← 等下一帧确保 visibility 已刷新
  → captureView(DecorView) → Bitmap
  → 恢复控件可见
  → 弹出分享弹窗传入 Bitmap
```

## Activity 端代码模板

```java
// import android.graphics.Bitmap;
// import android.graphics.Canvas;

private void takeScreenshotAndShare() {
    // 1. 隐藏不需要出现在截图中的控件（用 INVISIBLE 保留占位，避免布局抖动）
    backIV.setVisibility(View.INVISIBLE);
    shareIV.setVisibility(View.INVISIBLE);

    // 2. post 到下一帧，确保 visibility 变更已绘制
    View rootView = getWindow().getDecorView().getRootView();
    rootView.post(() -> {
        Bitmap screenshot = captureView(rootView);

        // 3. 恢复控件
        backIV.setVisibility(View.VISIBLE);
        shareIV.setVisibility(View.VISIBLE);

        if (screenshot == null) return;

        // 4. 弹出分享弹窗
        new CommonShareDialog.Builder(this)
                .setShareType(CommonShareDialog.TYPE_SHARE_IMG)
                .setShareBitmap(screenshot)
                .create()
                .show();
    });
}

private Bitmap captureView(View view) {
    try {
        Bitmap bitmap = Bitmap.createBitmap(view.getWidth(), view.getHeight(), Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        view.draw(canvas);
        return bitmap;
    } catch (Exception e) {
        return null;
    }
}
```

> **为什么用 `INVISIBLE` 不用 `GONE`？**  
> `GONE` 会触发 relayout，`INVISIBLE` 只触发 redraw，截图前后布局稳定不跳动。

## CommonShareDialog 扩展（TYPE_SHARE_IMG 支持）

项目中 `CommonShareDialog` 的 `TYPE_SHARE_IMG` 分支默认为空，需要手动补全：

### Builder 添加 `setShareBitmap`

```java
// 字段
private Bitmap shareBitmap;

// Builder 方法
public Builder setShareBitmap(Bitmap bitmap) {
    this.shareBitmap = bitmap;
    return this;
}

// create() 里赋值
dialog.shareBitmap = shareBitmap;
```

### handleWxShare — 微信图片分享

```java
case TYPE_SHARE_IMG:
    if (shareBitmap != null) {
        try {
            AppHelper.wxShareBitmap(scene, shareBitmap);
        } catch (Exception e) {
            new CenterToast(mContext).show(
                mContext.getString(R.string.Please_install_WeChat_first), Toast.LENGTH_SHORT);
        }
    }
    break;
```

`AppHelper.wxShareBitmap(int scene, Bitmap bitmap)` 已封装好微信图片发送逻辑。

### handleQQShare — QQ 图片分享

QQ SDK 图片分享需要**本地文件路径**，不能直接传 Bitmap：

```java
private void qqShareBitmap(Bitmap bitmap) {
    try {
        // 1. 先保存到本地 cache（AppUtils2.saveBitmap 返回绝对路径）
        String imgPath = AppUtils2.saveBitmap(mContext, bitmap);
        if (imgPath == null || imgPath.isEmpty()) {
            new CenterToast(mContext).show("分享失败，图片保存出错", Toast.LENGTH_SHORT);
            return;
        }
        Activity topActivity = ActivityUtils.getTopActivity();
        if (topActivity == null) return;

        // 2. 通过 QQShare.SHARE_TO_QQ_TYPE_IMAGE 分享本地图片
        android.os.Bundle params = new android.os.Bundle();
        params.putInt(QQShare.SHARE_TO_QQ_KEY_TYPE, QQShare.SHARE_TO_QQ_TYPE_IMAGE);
        params.putString(QQShare.SHARE_TO_QQ_IMAGE_LOCAL_URL, imgPath);
        params.putString(QQShare.SHARE_TO_QQ_APP_NAME, topActivity.getString(R.string.app_name));
        Tencent.createInstance(BuildConfig.QQ_APP_ID, mContext)
                .shareToQQ(topActivity, params, new IUiListener() {
                    @Override public void onComplete(Object o) {}
                    @Override public void onError(UiError uiError) {}
                    @Override public void onCancel() {}
                });
    } catch (Exception e) {
        new CenterToast(mContext).show("QQ未安装或分享失败", Toast.LENGTH_SHORT);
    }
}
```

### handleSaveOrCopy — 第四个按钮自适应

图片模式下第四个按钮（原"复制链接"）改为"保存图片"：

```java
private void handleSaveOrCopy() {
    if (shareType == TYPE_SHARE_IMG && shareBitmap != null) {
        // 保存到相册
        AppUtils.insertPictureToSystem(
            shareBitmap,
            "report_" + System.currentTimeMillis(),
            () -> new CenterToast(mContext).show("保存成功", Toast.LENGTH_SHORT)
        );
    } else {
        // 复制链接（原有逻辑）
        AppUtils2.copyStr(mContext, shareUrl);
        new CenterToast(mContext).show(
            mContext.getString(R.string.Copy_links_successfully), Toast.LENGTH_SHORT);
    }
}
```

## 关键工具类（本项目）

| 工具 | 方法 | 用途 |
|---|---|---|
| `AppHelper` | `wxShareBitmap(int scene, Bitmap)` | 微信图片分享（已封装） |
| `AppUtils2` | `saveBitmap(Context, Bitmap)` → `String` | 保存 Bitmap 到 cache，返回路径 |
| `com.lib.utils.AppUtils` | `insertPictureToSystem(Bitmap, String, Runnable)` | 保存 Bitmap 到系统相册 |
| `ActivityUtils` | `getTopActivity()` | 获取当前顶部 Activity（QQ 分享需要） |

## 陷阱

- `AppUtils2.saveBitmap` 只有两参数版本 `(Context, Bitmap)`，没有带文件名的三参数版本，不要传文件名
- `captureView` 截取的是 `DecorView`（包含状态栏），如果只想截内容区域，改用 `findViewById(android.R.id.content)` 或自定义根 View
- 微信图片分享 Bitmap 大小有上限（约 25MB），超大截图需缩放
- QQ SDK 图片分享不支持直接传 Bitmap，必须先落盘拿到本地路径
