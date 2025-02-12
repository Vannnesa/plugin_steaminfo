# 用法

1. 安装 NapCat 和 NoneBot
   [Napcat 安装](https://napneko.github.io/guide/napcat)用于 QQ 消息的 websocket 和 http 的收发
   [NoneBot 安装](”https://nonebot.dev/docs/”)是一个 Bot 插件框架 使用 Python 执行 高效异步。
   安装**Shell 版本**的 Napcat 和 NoneBot 的 nb-cli 脚手架后 看 Napcat 的**接入框架**文档 接入 NoneBot.

2. 安装本插件
   在 Nonebot 工作目录下新建一个**plugins**文件夹 在 plugins 文件夹内克隆本仓库

   ```
   git clone https://git.xn--z0s.top/https://github.com/Vannnesa/plugin_steaminfo.git
   ```

   (使用我的 git 加速网站进行加速 如已配置加速工具请删除前缀)

3. 在 Nonebot 的工作目录中添加环境变量

   | 环境变量               | 默认值 | 是否必填 | 说明                                                                                    |
   | ---------------------- | ------ | -------- | --------------------------------------------------------------------------------------- |
   | `STEAM_API_KEY`        | `N/A`  | 必填     | [点此获取]("https://steamcommunity.com/dev/apikey")<br>此插件的工作流程全部依赖该变量。 |
   | `STEAM_BROADCAST_TYPE` | `all`  | 非必填   | 可填 `part/all`                                                                         |

4. 在 Nonebot 工作目录新建 fonts 文件夹 下载 MiSans 兰亭字体解压到 fonts 文件夹中。当然你可以修改 init.py 选择已有字体。
5. 运行`nb run` 开始视奸之旅~
