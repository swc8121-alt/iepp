# IEPP arXiv submission package

This directory contains the reproducible source package for the first public arXiv submission.

## Build

```bash
cd paper
pdflatex -interaction=nonstopmode -halt-on-error iepp_arxiv_v1.tex
bibtex iepp_arxiv_v1
pdflatex -interaction=nonstopmode -halt-on-error iepp_arxiv_v1.tex
pdflatex -interaction=nonstopmode -halt-on-error iepp_arxiv_v1.tex
```

Upload `iepp_arxiv_v1.tex` and `references.bib` to arXiv. The generated PDF is a local verification artifact and does not need to be uploaded when TeX source is supplied.

## Claim boundary

The paper reports only merged and reproducible L1 evidence from the public repository. The authenticated Python reference profile and the supplemental two-VM Node.js harness are identified separately: the latter tests snapshot/restore orchestration and single-registry semantics with unsigned guest candidates. The paper does not treat open pull requests, roadmap items, L2--L4 mechanisms, entropy quality, runtime originality, clone resistance, distributed safety, or post-complete-compromise security as established results.
