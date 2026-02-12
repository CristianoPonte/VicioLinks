# Regra Geral
As UTMs que estarão presentes no link dependem se esse link é um link de captação ou de vendas.
Links de Captação → Captamos um lead por diferentes canais, mas ele ainda não comprou.
Links de Vendas → Link direto para uma página de vendas ou checkout.

## Captação

### UTMs Obrigatórias
utm_source (ferramenta) = Instagram | YouTube | Google | Meta | Site | WhatsApp | Email
utm_medium = 
utm_campaign = campanha padronizada (sem acento): enam90d_2026_1_captacao

### UTMs Opcionais
utm_content = Segmento / Lista
utm_term = detalhe extra que vale segmentar: perfil_vicio | perfil_concursos | lista_x | cta_a
utm_id = ID único do link (lnk_000123) para bater com seu Link Hub (deve ser gerado automaticamente)

## Vendas

### No caso de vendas, muda o padrão. As UTMs obrigatórias são:
utm_campaign = igual à usada na captação
src = de onde veio (nível macro/canais)
sck = quem vendeu? qual grupo? qual lista? qual operador?
xcode = utm_id

––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––

# Automações

## utm_campaign

A ideia é transformar utm_campaign num slug único e previsível gerado automaticamente a partir de:

Nível 1 — Produto (selecionado): VDE1F
Nível 2 — Turma (selecionado): 120d
Nível 3 — Lançamento (tipo de lançamento: evento | passariano | perpetuo)
Nível 4 – Data (mês/ano)

utm_campaign = {produto}_{turma}_{lancamento}_{data}
Ex.: vde1f_120d_passariano_07-24

1) Regras de normalização (o “slugger”)

Antes de concatenar, o sistema normaliza cada parte:
- minúsculo
- remover acentos
- trocar espaços por _
- remover caracteres especiais (deixar só a-z, 0-9, _, -)
- compactar repetição de _ (ex.: ___ vira _)
- trim (tirar _ do começo/fim)

2) Eu não quero ter que repetir isso toda vez que criar um utm_campaign. Deve ter um gerador só de utm_campaign e depois ele salvar todo o output como um campo inteiro.

3) Eu vou dar as pré-opções todas. Pré-opções de: produtos; turmas; lançamentos (tipos). Só a data que será adicionada na hora.

## utm_id // xcode

- Todo link gerado pelo Link Hub recebe um ID único (utm_id).
- Se o link for de Hotmart, o mesmo ID é aplicado também em xcode.

Resultado: você identifica o link exato que gerou a compra (via webhook/relatório), sem depender de src/sck.

Padrão do ID
Formato: lnk_000001 (prefixo fixo + número com zero à esquerda)

Regras:

- sempre minúsculo
- imutável após criado
- único (não pode repetir)

1) Mantenha um contador global no banco.
2) Ao criar um novo link, faça uma operação atômica (transação) para evitar duplicar ID quando duas pessoas gerarem ao mesmo tempo.

Se o destino do link for Hotmart (checkout/hotlink), então:
xcode = utm_id

## UTM_term

A utm_term sempre será: {tipo}_{dd-mm-yyyy}

O {tipo} será uma breve descrição que o usuário fará input. Depois, teremos underline e a data do disparo.

––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––

# Casos específicos

## Se utm_souce == "WhatsApp"

### Possibilidades de utm_medium:
- grupos
- api
- broadcast
- comercial
- suporte

Se utm_medium for grupos, possibilidades de utm_content:
- grupos_antigos
- grupos_atuais

Se utm_medium for api, possibilidades de utm_content:
- ex-alunos
- lista_lanc_atual
- lista_lanc_antigos

utm_term segue o padrão (seção automação).

/// PENSAR NAS AUTOMAÇÕES E FUNIS DE RENOVAÇÃO/VENDA NA API.

## Se utm_source == "Email"

### Possibilidades de utm_medium:
- newsletter
- marketing
- automacao

Se utm_medium for newsletter ou marketing:
utm_content é segmentação pode ser:
- lista_atual
- lista_antiga
- ex_alunos
- engajados

utm_term segue o padrão (seção automação).

## Se utm_source == "Site":

### Possibilidades de utm_medium:
- institucional
- plataforma_vde1f
- plataforma_vde2f
- plataforma_carreirasjur
- plataforma_enam

Possibilidades de utm_content em todos os casos:
- banner
- cupom_exclusivo
(Outras opções de segmentação e posicionamento)

utm_term não recebe data, somente personalização (caso necessário, não é obrigatório).