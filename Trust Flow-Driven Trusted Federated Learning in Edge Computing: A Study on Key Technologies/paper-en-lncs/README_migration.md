# LNCS 模板迁移与英文翻译流程

当前目录已经准备好：
- `main_en.tex`：LNCS 英文稿骨架（可直接编译）
- `main_cn.tex`：你的中文原稿备份
- `llncs.cls`、`splncs04.bst`：Springer LNCS 必需模板文件
- 所有已引用图文件（`*.pdf`）

## 1) 先确认模板可编译
```bash
cd "$(dirname "$0")"
latexmk -pdf -interaction=nonstopmode -halt-on-error main_en.tex
```

## 2) 按章节迁移（推荐顺序）
1. 标题、作者、单位
2. `Abstract` + `Keywords`
3. `Introduction`
4. `Background and Related Work`
5. `Method`
6. `Experiments`
7. `Conclusion`
8. `Appendix`
9. 参考文献

建议每完成一节就编译一次，避免一次性大改导致错误难定位。

## 3) 翻译时的硬规则（避免拒稿风险）
- 公式、符号、变量名不要翻译。
- 图号/表号/算法号不要改（如 `Fig.~\ref{...}`）。
- 引文键值不要改（如 `\cite{kairouz2021flsurvey}`）。
- 术语统一：
  - 联邦学习 -> Federated Learning
  - 可信执行环境 -> Trusted Execution Environment (TEE)
  - 后门攻击 -> Backdoor Attack
  - 攻击成功率 -> Attack Success Rate (ASR)
  - 假阳性率 -> False Positive Rate (FPR)

## 4) 参考文献迁移
你当前 `main_cn.tex` 使用的是 `thebibliography` 内联方式。
- 最快做法：直接把原 `thebibliography` 环境复制到 `main_en.tex` 末尾。
- 如需 BibTeX：改成
```tex
\bibliographystyle{splncs04}
\bibliography{refs}
```
并新增 `refs.bib`。

## 5) 常用编译命令
```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main_en.tex
latexmk -c   # 清理中间文件
```
