# Pod生命周期

## Pod相位（Phase）
- Pending：Pod已被K8s接受，但容器镜像未创建
- Running：Pod已绑定到节点，所有容器已创建
- Succeeded：所有容器成功终止
- Failed：至少一个容器失败终止
- Unknown：无法获取Pod状态

## 常见问题
### CrashLoopBackOff
原因：容器启动后立即崩溃
排查：检查容器日志、资源限制、配置错误

### ImagePullBackOff
原因：无法拉取镜像
排查：检查镜像名称、镜像仓库认证、网络连接
