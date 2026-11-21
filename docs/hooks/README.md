# hook：每台各自 add

自己寫的 hook 定義放 `hooks/<名字>.yaml`。skillshare 把 hook 存在 `config.yaml`（不進 repo，見
[architecture.md](../architecture.md#configyaml-為什麼不在-repo-裡)），所以每台要自己 add 一次，之後 yaml 改了就 edit：

```bash
skillshare hooks add <名字> --file ~/.config/skillshare/hooks/<名字>.yaml -g --sync   # 這台第一次
skillshare hooks edit <名字> --file ~/.config/skillshare/hooks/<名字>.yaml -g --sync  # pull 到新版
skillshare hooks list -g                                                           # 兩邊都是 ✓ 才算同步
```

其他 hook 指令看 [skillshare 官方文件](https://skillshare.runkids.cc)。

## 坑

- **Codex 不會跑沒審過的 hook。** add 或 edit 之後開 Codex 打 `/hooks`，把新的或改過的那條設成 trusted。（2026-11-07 記錄）
- **工具自己寫的 hook 不收。** herdr、codegraph 這些工具自己寫的 hook，`hooks list` 列成 `not managed`
  是正常的，sync 不會動它們。（2026-11-07 記錄）

## 一覽

| hook | 做什麼 |
|---|---|
| `speak` | Claude Code、Codex 回完話把回覆唸到個人電腦（dotfiles 的 `voice-out-speak`，沒勾 `snapserver` 的機器直接略過） |
