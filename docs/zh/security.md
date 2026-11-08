# 安全策略

## 威胁模型

Open Deck for MSFS 面向**可信的本地网络**（家庭 Wi-Fi、驾驶舱中的隔离网段、air-gapped 机器）。默认情况下：

- HTTP 和 WebSocket **不使用 TLS**（密码保护登录，但不加密流量）；
- 自动发现 UDP 信标未签名——网络上的任何主机都可以冒充网关；
- 客户端信任主机提供的文件（SHA-256 检查仅保护捐赠区块和界面完整性，而不保护服务器真实性）。

**不要将网关暴露到互联网**，也不要在存在不可信设备的网络中运行。对于访客网络，请使用单独的 VLAN 或添加带身份验证的自有反向代理。

## 已采取的措施

- **可选密码登录**：`config/auth.json` 中的 PBKDF2 哈希（210,000 次迭代），会话 TTL 12 小时，`HttpOnly` cookie，`SameSite=Lax`，原生客户端使用 Bearer，每分钟 5 次尝试限制，10 分钟一次性 QR 令牌（仅通过 `/?pair=` 接受）；
- 在主机启动时和浏览器中检查关键文件的完整性（SHA-256）。这是防止意外/故意修改的屏障，而不是密码学保护：清单可以通过 `--write` 命令重新计算；
- CSP `default-src 'self'`，禁止外部资源；
- 请求体大小限制、配置文件和命令校验；
- CORS 已关闭：第三方页面无法读取 API 响应；
- 对浏览器 POST/PUT 和 WebSocket 检查 `Origin`：外部 Origin 会收到 `403`（没有 Origin 的客户端被允许）；
- 按本地名称和 IP 列表检查 `Host`——防止 DNS 重绑定；未知 Host 会收到 `403`；
- 无需身份验证即可访问的只有登录页面、`/api/health`、`/api/integrity` 和 `/api/donation`（许可证要求）。如果未设置密码，网关会在控制台中打印警告；
- Android：WebView 跳转允许列表，捐赠中仅允许 `http(s)` 链接，禁用 file/content 访问。

## 报告漏洞

请**不要打开公开 issue**。请使用私密渠道：

- GitHub → Security → **Report a vulnerability**（Security Advisories），或
- 发送邮件至 `security@example.invalid`（发布前请替换为真实地址）。

请提供版本、复现步骤以及预期/实际行为。我们将在 7 天内回复。

## 支持的版本

| 版本 | 支持 |
| --- | --- |
| 0.1.x | 是 |

## 项目支持

- 作者：Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)
- 捐赠：[https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)
