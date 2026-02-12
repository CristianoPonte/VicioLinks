# LinksGenerator (VícioLinks)

## 1) Objetivo de negócio
O projeto centraliza a geração e governança de links com UTMs para reduzir erro operacional, padronizar nomenclatura e melhorar rastreabilidade entre marketing, CRM e checkout.

Existem dois fluxos principais:
- Captação: tráfego e aquisição de leads.
- Vendas: link com parâmetros adicionais para rastrear conversão em checkout.

## 2) Escopo funcional atual
- Autenticação JWT com RBAC (`admin`, `user`, `viewer`).
- Gerador de campanhas (`utm_campaign`) baseado em produto, turma, tipo e data.
- Gestão administrativa de:
  - campanhas (`launches`)
  - fontes (`source_configs`)
  - mediums e contents (dentro de `source_configs.config`)
  - produtos, turmas e tipos de lançamento
  - usuários
- Geração de links com:
  - normalização de UTMs
  - `utm_id` único
  - persistência em banco
  - auditoria de criação
- Repositório com filtros e exportação CSV.

## 3) Arquitetura técnica
### Backend
- FastAPI
- Pydantic
- Supabase (Postgres + API)
- JWT (`python-jose`) + hash de senha (`passlib`/`bcrypt`)

### Frontend
- HTML + CSS + JavaScript (SPA sem framework)
- Comunicação via `fetch` para rotas do backend

### Banco
Schema principal em `backend/schema.sql`.
Tabelas centrais:
- `users`
- `source_configs`
- `products`
- `turmas`
- `launch_types`
- `launches`
- `settings` (contador global)
- `links`
- `audits`

## 4) Contrato de UTMs (implementado)
### Captação
Parâmetros principais persistidos:
- `utm_source`
- `utm_medium`
- `utm_campaign`
- `utm_content` (opcional)
- `utm_term` (opcional)
- `utm_id` (campo `id` da tabela `links`)

### Vendas
Quando `link_type == "vendas"`, backend também preenche:
- mantém as mesmas UTMs de captação (`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`)
- **não envia `utm_id` na URL**
- `src = utm_source + "_" + utm_content`
- `sck = utm_medium`
- `xcode = utm_id` (conversão do ID interno para o parâmetro de vendas)

## 5) Regras de normalização
Função `slugger` (`backend/app/utils.py`):
- minúsculas
- remoção de acentos
- espaços para `_`
- mantém somente `[a-z0-9_-]`
- normaliza separadores repetidos

Padronizações adicionais:
- `utm_campaign`: sufixo de data em `mm-yy` (ex.: `..._01-24`)
- `utm_term`: data final em `dd-mm-yyyy` (ex.: `aaa_12-02-2026`)

## 6) Endpoints principais
Autenticação:
- `POST /token`
- `GET /users/me`

Admin/Configuração:
- `GET/POST /products`
- `GET/POST /turmas`
- `GET/POST /launch-types`
- `GET/POST/DELETE /launches`
- `GET/POST/DELETE /source-configs`
- `GET/POST/PUT/DELETE /users`

Operação:
- `POST /links/generate`
- `GET /links`

## 7) Segurança e permissões
- `admin`: acesso total, incluindo configurações e usuários.
- `user`: geração de links e operação (sem gestão administrativa crítica).
- `viewer`: leitura.

Dependências de autorização estão em `backend/app/auth.py`.

## 8) Seed inicial
No startup, backend tenta popular:
- `source_configs`
- `products`
- `turmas`
- `launch_types`
- usuários padrão (se tabela vazia)

Arquivo: `backend/app/main.py` (`startup_event`).

## 9) Decisões e correções recentes
- ID de link (`utm_id`) passou a priorizar incremento atômico via RPC `increment_link_counter`, reduzindo risco de colisão concorrente.
- Criação de `launch` evita envio de campos fora do schema SQL (`data_inicio`, `data_fim`, `_id`).
- `DELETE /source-configs/{slug}` protegido com role `admin`.
- Frontend corrigiu leitura de `term_config` para `source.config.term_config`.
- Tabela de links removeu `onclick` inline de cópia, com escape de conteúdo para reduzir risco de quebra/XSS.
- Fallback de cópia para navegadores/contextos sem Clipboard API.

## 10) Gap atual relevante (UTMs de vendas)
Pontos ainda a evoluir para vendas:
- Governança por canal de venda:
  - permitir regras diferentes por plataforma/checkout (ex.: Hotmart/Kiwify/Eduzz), não apenas regra fixa global.
- Validação semântica de `src/sck/xcode`:
  - hoje o backend monta os campos, mas não valida compatibilidade por source/medium/content.
- Templates de vendas:
  - presets por funil (remarketing, recuperação, lançamento, perpétuo).
- Rastreabilidade fim-a-fim:
  - faltam integrações nativas com eventos de venda (webhook de plataforma) para fechar ciclo `utm_id -> venda`.

## 11) Como rodar (resumo)
Pré-requisitos:
- Python 3
- Variáveis de ambiente: `SUPABASE_URL`, `SUPABASE_KEY`, `SECRET_KEY`

Passos típicos:
1. Instalar dependências do backend: `pip install -r backend/requirements.txt`
2. Aplicar schema no banco (`backend/schema.sql`).
3. Subir API (exemplo): `uvicorn backend.app.main:app --reload`
4. Abrir frontend servido pela própria API (mount estático em `/`).

## 12) Riscos e limitações atuais
- Não há suíte automatizada de testes no repositório.
- Seed inclui credenciais padrão em ambiente vazio (adequado só para dev inicial).
- Regras de UTM ainda são parcialmente dirigidas pela UI (backend com validações simplificadas).
- CORS está aberto para `*`.

## 13) Backlog recomendado (prioridade)
1. Implementar política de validação de UTM no backend por `source_config` (não só pela UI).
2. Criar módulo de regras de vendas por plataforma com contrato explícito.
3. Adicionar testes automatizados (unit + integração de API).
4. Endurecer segurança para produção (CORS, secrets, rotação de senhas, remover usuários seed padrão).
5. Instrumentar métricas e trilha de auditoria consultável por período/canal.

---
Última atualização: 12/02/2026
