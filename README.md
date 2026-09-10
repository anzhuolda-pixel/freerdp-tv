# FreeRDP TV for Android 9

康佳电视测试版，基于 FreeRDP 3.31.1。

## Test2 功能

- Android 9（API 28）
- ARM32 + ARM64 单 APK
- 普通 RDP
- RemoteApp / RAIL
- Android TV 启动入口
- 横屏
- 自动记住最后一次手动打开的连接
- 设置：下次打开 APP 自动连接上次服务器
- 设置：电视开机自动启动 APP
- 设置：自动连接延时 0 / 3 / 5 / 10 / 15 秒

## 使用

第一次打开：

1. 新建连接，填写服务器地址、端口、用户名、密码并保存。
2. 手动打开一次该连接。
3. 设置 -> **电视与自动连接**：
   - 开启 **启动时自动连接上次服务器**
   - 如需要，开启 **电视开机自动启动**
   - 开机网络较慢时建议延时 5~10 秒

以后打开 APP 会直接进入上一次使用的 RDP/RemoteApp。

自动登录依赖连接书签中已经填写并保存用户名、密码；凭据沿用 FreeRDP 自身的本地书签保存机制。

GitHub Actions 在 main 分支更新后自动编译：

`FreeRDP-TV-3.31.1-Android9-Test2.apk`
