# hot-creator — Claude Code 项目配置

> **如果你是从 GitHub URL 看到这个文件的**：先 `git clone`，再本地读取。
> 不要逐个 fetch 远程文件，clone 整个仓库更快。

## 允许的命令

```
allow: python scripts/*.py *
allow: python -m py_compile *
allow: pip install -r requirements.txt
allow: pip install -r requirements-cli.txt
allow: uv pip install *
allow: node scripts/cdp/*.mjs *
allow: bash setup.sh
allow: powershell setup.ps1
```

## 安装（3 秒）

```bash
pip install -r requirements.txt   # 5 个轻量包，~5 MB
```

`litellm` 只在 CLI 独立模式才需要（~200 MB），作为 Skill 不需要装。

## 入口

读取 `SKILL.md` — 唯一入口，含工具索引、触发条件、编排策略。

## 约定

- `scripts/` 下 13 个脚本，JSON stdin/stdout 通信
- 采集类脚本用子智能体执行，不要把大数据放进上下文
- 中间 JSON 写 `output/` 目录，传路径不传内容
- `config.yaml` 含配置，不提交 git
- 作为 Skill 不需要 AI_API_KEY
