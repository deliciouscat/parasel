# Parasel Skill Directory

Documentation for AI code agents using the Parasel framework.

## Directory Structure

```
parasel-skill/
├── SKILL.md              # Main skill file (metadata + quick start)
├── references/           # Detailed documentation
│   ├── core-concepts.md     # Architecture and key concepts
│   ├── usage-guide.md       # Step-by-step implementation guide
│   ├── patterns.md          # Common pipeline patterns
│   ├── troubleshooting.md   # Problem solving guide
│   └── api-reference.md     # Complete API documentation
├── examples/             # Working examples
│   ├── simple_pipeline.py   # Basic Serial/Parallel
│   ├── multi_language.py    # ByArgs example
│   ├── web_recommend.py     # Real-world pipeline
│   └── fastapi_deploy.py    # API deployment
├── assets/               # Templates and resources (empty for now)
└── README.md            # This file
```

## Usage

1. **Start**: Read `SKILL.md` for overview and when to use Parasel
2. **Learn**: Navigate to specific `references/*.md` as needed
3. **Implement**: Reference `examples/*.py` for code patterns

### Run Examples

```bash
# Simple pipeline
python examples/simple_pipeline.py

# Multi-language processing
python examples/multi_language.py

# Web recommendation (realistic example)
python examples/web_recommend.py

# FastAPI deployment
python examples/fastapi_deploy.py
```

### Documentation Index

- `SKILL.md` - Entry point: What, when, quick start
- `references/core-concepts.md` - Architecture, Context, Nodes, ByArgs/ByKeys
- `references/usage-guide.md` - Step-by-step implementation
- `references/patterns.md` - 12 common pipeline patterns
- `references/troubleshooting.md` - Common issues and solutions
- `references/api-reference.md` - Complete API documentation


## Framework Paths

**Framework code**: `/Users/deliciouscat/projects/parasel/parasel/`  
**Real project example**: `/Users/deliciouscat/projects/WizPerch-ai-pipeline/`
