# JasperYux's Blog

[记录、叙述、回忆](https://jasperyux.github.io/)

文章来源于 [gitblog 的公开 Issues](https://github.com/JasperYux/gitblog/issues)，前端在构建时生成静态 HTML。阅读文章不需要 JavaScript，也不需要浏览器持有 GitHub 令牌。

## 本地开发

使用 Python 3.12，安装 `requirements.txt`，运行 `python scripts/build.py`，再运行 `python -m http.server 8000 --directory site`。

- `scripts/build.py`：读取公开文章，生成首页、正文、目录、RSS 和 sitemap。
- `assets/`：样式、头像与旧链接兼容脚本。
- `site/`：构建产物，不提交到 Git。

GitHub Actions 使用自带的临时令牌构建。默认每小时第17、47分钟同步，也可以在 Actions 中手动运行 **Build and deploy blog**。定时任务可能延迟；长时间没有仓库活动时 GitHub 可能暂停定时运行，可手动重新启用。发布周报后想立即更新，可执行：

```sh
gh workflow run deploy.yml -R JasperYux/jasperyux.github.io
```

GitHub Pages 发布源为 GitHub Actions。旧站 `#/posts/编号` 链接会跳转到新文章地址。原有页面中的混淆凭据已从当前源码移除；旧凭据若仍有效，应在 GitHub 的 token 设置中撤销，删除当前文件不等于撤销历史凭据。

首页采用左侧个人信息、右侧文章标题列表的布局，仅展示标题、更新时间和分类，不包含正文摘要；手机端个人信息显示在顶部。
