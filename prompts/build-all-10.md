You are building Period 2 Bohrium Product Weekly Contest submissions in this workspace.

Workspace: /aisi-nas/guomingyu/agent_dev/agent-challenge/bohrium-product-261104
Contest: https://play.bohrium.com/competition/bohr-product?period=2
Theme: AI literature reading and academic writing. Ten Skill challenges; each scored 0-100 (effect 40 / gain vs bare agent 25 / novelty 15 / reliability 10 / reuse-docs 10). Prizes rank on the sum of all ten.

Read first:
- docforge-reuse.md
- challenges/*.json (full public statements)
- vendor/doc-forge (MIT; useful for bibliography / gates / LaTeX-adjacent writing tracks; do NOT vendor-copy huge trees into Skill bundles)

Goal: implement ONE Harbor-ready Skill package per challenge under skills/<slot>-<short-name>/, for ALL ten slots below. Then pack each into submissions/<slot>/ for upload (SKILL.md + scripts/resources + usage doc + one labeled minimal example).

Slots (period page order):
01 product-arena-08-3027d350 文献文档解析
02 product-arena-01-5a9928c1 文献翻译
03 product-arena-06-6d8cf72b 文献总结与结构化笔记
04 product-arena-09-0e8befd4 Nanopublication
05 product-arena-10-760d1a0b 文献知识图谱构建
06 product-arena-02-7051d92d 学术语言润色
07 product-arena-03-429cc14d 参考文献与引用管理
08 product-arena-04-4b82ad21 引言与相关工作写作
09 product-arena-05-64faa4a2 方法与实验章节写作
10 product-arena-07-865de7e4 LaTeX 写作与编译

Harbor contract (from statements):
- Skill installs under /skills/weekly-skill
- Input: /input/case.json + task.md (+ real PDFs/materials when provided)
- Work under /app/work; final /app/output/result.json with all output_contract fields, case_id, honest status/sources/uncertainty/change records
- Budget awareness: 64 model requests, 900s, 16384 tokens/response
- Skill resources: ≤50 UTF-8 text files, ≤500KB each, ≤2MB total, no symlinks
- Do NOT submit prepared answers or formal test outputs; Skill must run on organizer fixed cases
- Focus one sharp sub-problem per track if needed; full systems not required
- Prefer real, verifiable improvements vs bare agent (structure, provenance, evidence spans)

Implementation rules:
1. Each skill dir MUST contain SKILL.md with valid YAML frontmatter name + description, plus runnable helpers and USAGE.md and examples/minimal/
2. Keep bundles small and text-first. Reuse ideas from vendor/doc-forge where they fit (esp. 07 bibliography, 10 latex hygiene) by extracting tiny modules into the Skill, not shipping the whole package.
3. Write skills/README.md indexing all ten with challenge ids and one-line focus.
4. Write ATTEMPTS.md noting what was built and intended submission order.
5. Do not invent Playground scores. Do not commit secrets/.env.
6. After all ten Skills exist and look complete, stop. Do not git push yourself; the coordinator will push.

Success criteria:
- skills/ has ten complete packages matching the ten challenge ids
- submissions/ has ten upload-ready trees
- skills/README.md + ATTEMPTS.md updated
- No placeholder-only SKILL.md; each must encode a concrete method for its track
