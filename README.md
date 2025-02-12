#用法:
1. 安装NapCat和NoneBot
   [Napcat安装](”https://napneko.github.io/guide/napcat”)用于QQ消息的websocket和http的收发
   [NoneBot安装](”https://nonebot.dev/docs/”)是一个Bot插件框架 使用Python执行 高效异步。
安装**Shell版本**的Napcat和NoneBot的nb-cli脚手架后 看Napcat的**接入框架**文档 接入NoneBot.

2.安装本插件
   在Nonebot工作目录下新建一个**plugins**文件夹 在plugins文件夹内克隆本仓库
````
git clone https://git.xn--z0s.top/https://github.com/Vannnesa/plugin_steaminfo.git
````
(使用我的git加速网站进行加速 如已配置加速工具请删除前缀)
在Nonebot的工作目录中添加环境变量
|环境变量|默认值|是否必填|说明|
|STEAM_API_KEY|N/A|必填|[点此获取]("https://steamcommunity.com/dev/apikey")此插件的工作流程全部依赖该变量。|
|STEAM_BROADCAST_TYPE|all|非必填|可填part/all|

在Nonebot工作目录新建fonts文件夹 下载MiSans兰亭字体解压到fonts文件夹中。当然你可以修改init.py 选择已有字体。
运行`nb run` 开始视奸之旅~
