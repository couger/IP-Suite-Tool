# IP-Suite-Tool

**实验性测试项目（Experimental）。** 个人维护的网络地址处理工具，仅供学习、研究和测试。使用前请备份原始文件；地址结果和设备配置须人工复核。

提供五个页面：IPv4/IPv6 转换、子网计算、IP 文本替换、工作统计及 IP 申请资料归档。

## 当前限制

- IP 文本替换不能清除全部企业或个人信息；批注、页眉、外链、图片与元数据等仍需另行检查。不要直接把结果当成可公开文件。
- IP 分配页面目前仅归档图片和申请表，尚未连接地址池。独立分配核心使用静态占位地址，不能用于生产分配。
- 规划编辑器只导出首表数据，不承诺保留原文件中的公式、多表、宏或样式。
- Windows Excel OLE 附件嵌入需要安装桌面 Excel；其他环境可不嵌入附件导出统计。
- 公开示例全部从零创建，使用虚构单位、站点、人员和文档示例地址，与企业实际网络无关。

## 从源码运行

使用 Python 3.11 或更新版本，系统须提供 Tk。Windows Python 安装时选择 Tcl/Tk；Linux 请另装发行版提供的 python3-tk。

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python src/main.py
```

在 IP 申请页面依次选择 `examples/network_plan.xlsx`（规划）、`examples/allocations.xlsx`（总表）和 `examples/requests.xlsx`（申请）；图片由使用者自行选择测试图片。统计页面支持普通文件名，也兼容旧版 `pl`/`add` 加 12 位数字的文件名前缀。

个人前缀、上次文件路径和日志放在系统用户数据目录，源码目录不保存运行配置。可通过 `IP_SUITE_DATA_DIR` 指定自己的数据目录。旧版配置不会被自动导入；请在界面重新选择文件、添加自己的实例。

## 验证与构建

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/check_public_content.py
python scripts/build.py
# 可选：生成带控制台的开发目录版本
python scripts/build.py --mode development
# Windows 示例；其他平台传入对应的可执行文件
python scripts/check_public_content.py --binary bin/IP-Suite-Tool.exe
```

构建只纳入静态字段映射、干净默认实例和图标。企业表格、用户配置和日志不得加入打包资源。自动检查只能辅助审阅，不能判断所有业务资料或代码权属。

## 文档与许可

- [示例说明](examples/README.md)
- [项目结构与目录职责](docs/PROJECT_STRUCTURE.md)
- [格式契约与兼容性](docs/PUBLIC_COMPATIBILITY.md)
- [安全与隐私](SECURITY.md)
- [整改状态与发布条件](docs/REMEDIATION_STATUS.md)
- [参与开发](CONTRIBUTING.md)
- [Apache-2.0 许可证](LICENSE)

当前版本使用独立历史，示例采用从零设计的通用字段。不要合并原私有业务历史，也不要上传未经重新检查的旧安装包。旧仓库已删除并以同名私有仓库重建；技术检查通过不代表获得源码公开授权，源码公开授权仍待确认，自动发布保持阻止状态。
