# 资源管理

## CPU和内存限制
- requests：容器请求的最小资源
- limits：容器可使用的最大资源

## 常见问题
### OOMKilled
原因：容器内存使用超过limits
解决：增加memory limits或优化应用内存使用

### CPU节流
原因：CPU使用超过limits
解决：增加CPU limits或优化应用CPU使用
