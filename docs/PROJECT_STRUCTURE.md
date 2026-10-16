# 项目结构

```text
IP-Suite-Tool/
├── src/                    当前应用入口、界面、核心模型及静态资源
│   ├── main.py             五页应用入口
│   ├── ip_*.py             各功能页面
│   ├── models/             当前核心计算、转换、IP 替换和分配逻辑
│   ├── ui/                 通用界面组件与样式
│   ├── utils/              表格契约、资源路径和隐私日志
│   ├── cfgs/               静态字段映射
│   ├── defaults/           干净的默认实例
│   └── ico/                应用图标
├── tests/                  自动测试
│   └── helpers/            合成数据生成与批量验证工具
├── examples/               随源码发布的纯净示例
├── scripts/                当前构建入口和公开内容检查
├── packaging/              唯一 PyInstaller 配置及打包钩子
├── docs/                   当前说明、兼容性边界与验证记录
├── .github/workflows/      自动测试、隐私检查及构建
├── requirements.txt        应用依赖
├── release-readiness.json  公开授权及旧仓库处置状态
├── requirements-dev.txt    测试、构建依赖
└── pytest.ini              统一测试发现与导入路径
```

`bin/` 和 `build/` 是忽略的本地生成目录。用户前缀、文件路径及日志位于系统用户数据目录，不属于源码。`test_outputs/` 仅用于辅助工具生成的合成文件，不提交。

所有主程序构建，包括 CI，都调用 `scripts/build.py`，使用 `packaging/IP-Suite-Tool.spec`。开发模式与单文件发布模式共享同一资源白名单；相对路径以项目位置确定，执行者无需先进入 `src`。

从根目录运行 `python -m pytest -q`。需要生成额外测试数据时，可运行 `python tests/helpers/generate_anonymizer_excel_test.py` 或 `python tests/helpers/monthly_stats_bulk_fixture.py`；批量 OLE 验证工具需要 Windows 桌面 Excel。

迁移历史工具不改变当前主程序的功能范围：归档界面仍未接入生产地址池，IP 替换仍不保证整份文档完全脱敏。

历史工具与旧模板保存在仓库外的私有归档，不属于提交内容。
