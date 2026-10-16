# 参与开发

请使用虚构样例和文档地址；不要提交运行配置、业务表格、日志或安装程序。

安装 `requirements-dev.txt` 中的依赖后，从项目根目录运行 `python -m pytest -q` 和 `python scripts/check_public_content.py`。测试集中在 `tests/`，合成数据工具在 `tests/helpers/`。构建统一使用 `python scripts/build.py`；修改表格读取、配置或打包时，应验证首表、列名、空申请单号、普通文件名、旧列名导入和打包白名单。GUI 变更还需要在真实桌面操作验证。

发布分支应使用 GitHub noreply 提交邮箱。不要合并私有业务仓库的旧历史。公开新版本时标注 Experimental，并使用预发布状态。


公开样例采用通用十列申请表和四列规划表；测试仅使用合成数据。修改样例必须重新审查内部结构和内容，随后更新 manifest，不能仅修改哈希以绕过检查。

发布前必须获得源码公开授权，并完成原私有仓库处置确认；不能用测试通过代替授权。见 `docs/REMEDIATION_STATUS.md`。
