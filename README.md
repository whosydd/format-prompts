# Infinite Canvas Prompt Sync

本仓库从以下三个公开仓库定期读取数据，并转换为 Infinite Canvas 支持的 JSON 数组：

- [BigPengSays/awesome-gpt-image-2-prompts](https://github.com/BigPengSays/awesome-gpt-image-2-prompts)
- [apimodels/gpt-image-2-5-prompts](https://github.com/apimodels/gpt-image-2-5-prompts)
- [stretchcloud/awesome-gpt-image-prompt-2.5](https://github.com/stretchcloud/awesome-gpt-image-prompt-2.5)

转换结果位于 [`data/prompts.json`](data/prompts.json)。该文件只包含 Infinite Canvas 格式的七个字段：`id`、`title`、`prompt`、`description`、`coverUrl`、`referenceImageUrls` 和 `tags`。

## 字段映射

- `id`、`title`、`prompt` 保留上游内容。数字 ID 会增加来源前缀；APImodels 使用英文标题，中文标题放入 `description`。
- `description` 保留作者、模型、来源链接和来源记录；有提供时还包含中文标题、摘要、渠道、语言相关说明或图片署名链接。
- `coverUrl` 使用 BigPengSays 来源的 `image_url`，缺少时使用仓库 `previews/` 图片的 raw GitHub URL。APImodels 使用 `example_image`，缺图时留空。StretchCloud 使用仓库 `data/images/` 中对应的预览图。
- `referenceImageUrls` 固定为空数组。上游图片是原帖或成品预览，没有标记为生成输入的图片，因此不把它们误作参考输入。
- `tags` 包含上游分类、模型标识和来源仓库；有提供时还包含语言、质量等级、渠道、主题和画幅。
- 多个来源出现相同 `id` 时只输出一条记录。按 `SOURCES` 顺序保留首个来源的内容，并合并来源标记。数字 ID 使用不同来源前缀，避免与其他来源冲突。

图片只保留原始外链或生成仓库预览链接，不会下载或托管。外链可能失效。

## 本地运行

需要 Python 3.10 或更高版本，无需安装第三方依赖。

```bash
python3 converter.py
python3 -m unittest discover -s tests
```

转换器会从上游读取最新数据并重写 `data/prompts.json`。也可以用 `--output` 指定输出路径。

## 自动同步

GitHub Actions 每周一 07:17 UTC 运行，也支持在 Actions 页面手动触发。检测到数据变化时，工作流会将更新提交到默认分支。仓库设置需要允许 Actions 写入内容。

## 来源与权利

本仓库保留每条记录的作者和来源链接。BigPengSays 来源当前没有 `LICENSE` 文件。APImodels 的 MIT 许可仅覆盖整理内容，明确排除第三方 prompt 和图片。StretchCloud 将 prompt 以 MIT 许可发布，其预览图要求注明并链接回 Devault 的 Figma 页面；转换结果保留了该署名链接。本仓库不扩大或替代上游许可，使用者应查看对应作者及来源的条款。
