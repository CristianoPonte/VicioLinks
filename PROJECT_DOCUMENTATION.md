# 🔗 VícioLinks: O Hub de Governança e Inteligência UTM

Este documento é a fonte única de verdade (SSoT) para o projeto **VícioLinks**. Ele consolida decisões de negócio, especificações técnicas, contratos de rastreamento e orientações para evolução do sistema.

---

## 🎯 1. Visão Executiva e Decisões de Negócio

O VícioLinks não é apenas uma ferramenta de "copiar e colar links". Ele é um **motor de governança** criado para eliminar o "caos das UTMs" que distorce relatórios no GA4, CRM e plataformas de Ads.

### Decisões Críticas Tomadas:
*   **Normalização Forçada**: Identificamos que 40% dos erros de tracking vinham de maiúsculas misturadas ou acentos. O sistema agora força `lowercase` e remove acentos em nível de Backend.
*   **Contrato de IDs Únicos**: Cada link gerado recebe um ID atômico (`lnk_XXXXXX`). Isso permite que o analista de dados ignore a URL e baseie toda a sua query SQL no ID, que é imutável.
*   **Descentralização com Controle**: O Admin permite que gestores criem regras (Canais/Meios), enquanto a operação apenas "seleciona" opções válidas, eliminando erros humanos no dia a dia.

---

## 🧠 2. Lógica Jurídica de UTMs (Governança)

O sistema diferencia dois fluxos vitais de negócio:

### A. Fluxo de Captação (Marketing Padrão)
Utilizado para gerar tráfego para LPs, Páginas de Vendas e Inscrições. Segue o padrão GA4 clássico:
*   `utm_source`: A ferramenta/origem (ex: meta, whatsapp).
*   `utm_medium`: O tipo de tráfego (ex: stories, grupos).
*   `utm_campaign`: O slug gerado pelo motor (ex: `vde1f_120d_evento_0226`).
*   `utm_term`: Usado para detalhes dinâmicos (como datas no caso de e-mail).

### B. Fluxo de Vendas (Contrato Técnico de Checkout)
Quando o modo é alterado para **Vendas**, o sistema injeta parâmetros específicos para rastreio de conversão direta em plataformas como Hotmart/Eduzz/Kiwify:
*   `src` (Source de Venda): Mapeado automaticamente do `utm_medium`.
*   `sck` (Checkout Cookie): Composto pela união de `utm_source` + `utm_content`. Ex: `meta_bio`.
*   `xcode`: Mapeado diretamente do `utm_id` (O ID atômico do link).

---

## 🏗️ 3. Arquitetura Técnica

### 🧬 Stack de Elite
*   **FastAPI (Backend)**: Escolhido pela velocidade de execução e validação automática de tipos via Pydantic.
*   **Firestore (Database)**: Banco de dados NoSQL serverless da Google Cloud, que permite alta escalabilidade e persistência em tempo real.
*   **Vanilla JS (Frontend)**: Arquitetura SPA "zero-framework" para manter o carregamento instantâneo e total controle sobre o DOM.

### 📁 Estrutura de Pastas
```text
/backend/app/
  ├── main.py       # Orquestração de rotas e lógica de API
  ├── models.py     # Contratos de dados (Pydantic schemas)
  ├── utils.py      # O "Coração": Slugger, Normalizer e URL Builder
  ├── database.py   # Conector Firestore com fallback para LocalStorage (db.json)
  └── auth.py       # Motor de Autenticação JWT e RBAC
/frontend/
  ├── index.html    # Estrutura UI
  ├── style.css     # Design System (Glassmorphism)
  └── app.js        # Lógica de interface e chamadas de API
```

---

## 💎 4. Design System: "Compact Technical"

A interface segue uma estética **Premium Dark Mode** focada em densidade de informação:

*   **Glassmorphism**: Transparências (`backdrop-filter`) e cores vibrantes em gradiente para um feeling de cockpit de avião.
*   **Purple Code Effect**: Elementos como IDs e Slugs são renderizados dentro de tags `<code>` com fundo roxo acentuado, destacando o que é "dado de sistema" vs "texto de usuário".
*   **Micro-interações**: Hover effects suaves em botões `btn-primary` e `btn-secondary` para feedback instantâneo.

---

## 🔐 5. Segurança e Controle de Acesso (RBAC)

O sistema implementa uma camada de segurança robusta baseada em **OAuth2 com JWT (JSON Web Tokens)**, garantindo que apenas usuários autorizados interajam com os dados.

### Níveis de Permissão:
*   **👑 Admin (Administrador)**: Acesso total ao sistema. Pode gerenciar usuários, configurar regras de UTM (Sources/Mediums), visualizar logs e gerar links.
*   **✍️ Editor (Editor)**: Focado na operação. Pode gerar novos links UTM e visualizar o repositório, mas não tem acesso às configurações administrativas ou gestão de usuários.
*   **👁️ Viewer (Visualizador)**: Acesso de "apenas leitura". Pode navegar pelo repositório de links e pesquisar informações, mas não tem permissão para criar ou modificar nada.

### Gestão de Usuários:
O sistema conta com um módulo interno de **User Management** (exclusivo para Admins) acessível via ícone de perfil 👤 na barra de navegação. Este módulo permite:
*   Criação de novos acessos com senhas criptografadas (`bcrypt`).
*   Alteração de cargos e permissões em tempo real.
*   Exclusão de contas (com proteção para a conta mestre do sistema).

---

## 🛠 6. Manutenção e Operação

### Gerador de Slugs (Engine)
O gerador segue a regra lógica: `[PRODUTO]_[TURMA]_[TIPO]_[MES][ANO]`.
A normalização (`slugger`) realiza:
1.  Minúsculas.
2.  Remoção de acentos/diacríticos.
3.  Troca de espaços por `_`.
4.  Compactação de underscores repetidos.

### Administração e Cascata
No Admin, ao configurar uma **Source**, você define quais **Mediums** são permitidos. Cada Medium, por sua vez, pode ter uma lista restrita de **Contents**. No gerador de links, as opções aparecem dinamicamente com base nas seleções anteriores.

---

## 🚀 7. Roadmap e Futuro
*   [ ] **Dashboard BI**: Visualização de volume de links por campanha/canal direto no App.
*   [ ] **Integração Webhook**: Disparar eventos para o Slack/Discord cada vez que uma nova Campaign for criada.
*   [ ] **Encurtador de Link**: Módulo para reduzir os links gigantes de UTM para versões curtas (`vicio.li/id`).

---
> **Documentação finalizada em 11/02/2026. Este documento substitui todos os READMEs e User Stories anteriores.**
