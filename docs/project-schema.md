
---

## 📄 2️⃣ `project-schema.md`
```markdown
# Project Schema - CIP

## Definición de proyecto
Cada proyecto crypto = unidad de análisis: token, repositorios, redes sociales, contratos on-chain.  

Ejemplo YAML (`project.yaml`):
```yaml
project_id: arbitrum
name: Arbitrum
category: layer2
description: Ethereum Layer 2 optimistic rollup

token:
  symbol: ARB
  network: ethereum

github:
  repositories:
    - owner: OffchainLabs
      repo: arbitrum
    - owner: OffchainLabs
      repo: nitro

social:
  twitter:
    - handle: arbitrum
    - handle: OffchainLabs
  reddit:
    - subreddit: arbitrum

onchain:
  networks:
    - ethereum
  contracts:
    - name: ArbitrumBridge
      address: "0x..."
