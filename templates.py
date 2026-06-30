"""25 ferramentas de IA — templates com system prompts e campos de formulário."""


def _fmt(template: str, inputs: dict) -> str:
    result = template
    for k, v in inputs.items():
        result = result.replace(f"<<{k}>>", str(v))
    return result


TEMPLATES: dict[str, dict] = {
    "01_roteiro_video": {
        "id": "01_roteiro_video",
        "nome": "Gerador de Roteiros de Vídeo",
        "icone": "🎬",
        "categoria": "Conteúdo",
        "descricao": "Roteiros personalizados por especialidade e tom de voz",
        "campos": [
            {"nome": "especialidade", "label": "Especialidade / Nicho", "tipo": "text", "placeholder": "Ex: Nutrição, Marketing Digital, Finanças"},
            {"nome": "tom", "label": "Tom de Voz", "tipo": "select", "opcoes": ["Profissional", "Descontraído", "Educativo", "Inspirador", "Humorístico"]},
            {"nome": "duracao", "label": "Duração do Vídeo", "tipo": "select", "opcoes": ["30 segundos", "1 minuto", "3 minutos", "5 minutos", "10 minutos"]},
            {"nome": "tema", "label": "Tema / Assunto do Vídeo", "tipo": "textarea", "placeholder": "Descreva o assunto principal do vídeo"},
        ],
        "system_prompt": """Você é roteirista profissional para vídeos de <<especialidade>>.
Crie roteiro completo para vídeo de <<duracao>>, tom <<tom>>.
Tema: <<tema>>

ESTRUTURA:
1. HOOK (3-5s — prende atenção imediatamente)
2. APRESENTAÇÃO (quem fala, do que se trata)
3. DESENVOLVIMENTO (conteúdo em tópicos objetivos com tempo estimado por seção)
4. CTA (call to action direto)
5. ENCERRAMENTO

Marque: [B-ROLL], [PAUSA], [ÊNFASE] onde relevante. Tom: <<tom>>.""",
    },

    "02_chatbot_atendimento": {
        "id": "02_chatbot_atendimento",
        "nome": "Chatbot de Atendimento para Site",
        "icone": "💬",
        "categoria": "Atendimento",
        "descricao": "Assistente que responde dúvidas, faz triagem e captura leads",
        "campos": [
            {"nome": "empresa", "label": "Nome da Empresa", "tipo": "text", "placeholder": "Ex: Clínica Vida Plena"},
            {"nome": "segmento", "label": "Segmento / Setor", "tipo": "text", "placeholder": "Ex: Clínica médica, E-commerce, Consultoria"},
            {"nome": "servicos", "label": "Principais Serviços / Produtos", "tipo": "textarea", "placeholder": "Liste os principais serviços ou produtos oferecidos"},
            {"nome": "tom", "label": "Tom do Atendimento", "tipo": "select", "opcoes": ["Formal", "Amigável", "Neutro", "Descontraído"]},
        ],
        "system_prompt": """Você é especialista em criação de chatbots de atendimento.
Empresa: <<empresa>> | Segmento: <<segmento>> | Tom: <<tom>>
Serviços/Produtos: <<servicos>>

Crie o script completo do chatbot com:
1. SAUDAÇÃO INICIAL (apresentação + opções de menu)
2. FLUXO DE DÚVIDAS FREQUENTES (10+ perguntas com respostas)
3. TRIAGEM (identificar necessidade e direcionar ao setor correto)
4. CAPTURA DE LEAD (nome, email, telefone, necessidade)
5. ENCERRAMENTO (próximos passos + despedida)

Formato: [CHATBOT]: mensagem / [USUÁRIO]: resposta típica.""",
    },

    "03_legendas_redes": {
        "id": "03_legendas_redes",
        "nome": "Gerador de Legendas para Redes Sociais",
        "icone": "📱",
        "categoria": "Conteúdo",
        "descricao": "IA produz legenda, CTA e hashtags a partir de tema ou roteiro",
        "campos": [
            {"nome": "plataforma", "label": "Plataforma", "tipo": "select", "opcoes": ["Instagram", "LinkedIn", "TikTok", "Facebook", "Twitter/X", "YouTube"]},
            {"nome": "tema", "label": "Tema ou Resumo do Conteúdo", "tipo": "textarea", "placeholder": "Sobre o que é o post/vídeo?"},
            {"nome": "tom", "label": "Tom de Voz", "tipo": "select", "opcoes": ["Inspirador", "Educativo", "Humorístico", "Provocativo", "Vendas", "Storytelling"]},
            {"nome": "objetivo", "label": "Objetivo do Post", "tipo": "select", "opcoes": ["Engajamento", "Vendas", "Seguidores", "Tráfego para site", "Autoridade"]},
        ],
        "system_prompt": """Você é especialista em copywriting para redes sociais.
Plataforma: <<plataforma>> | Tom: <<tom>> | Objetivo: <<objetivo>>
Tema: <<tema>>

Crie 3 versões de legenda otimizadas para <<plataforma>>:

VERSÃO 1 — CURTA (até 150 caracteres):
[legenda] + [CTA] + [hashtags]

VERSÃO 2 — MÉDIA (até 300 caracteres):
[legenda com gancho] + [desenvolvimento] + [CTA] + [hashtags]

VERSÃO 3 — LONGA (storytelling / educativa):
[gancho] + [história/conteúdo] + [lição/benefício] + [CTA forte] + [hashtags]

Finalize com lista de 15-20 hashtags relevantes separadas.""",
    },

    "04_proposta_comercial": {
        "id": "04_proposta_comercial",
        "nome": "Gerador de Propostas Comerciais",
        "icone": "📋",
        "categoria": "Vendas",
        "descricao": "Cliente preenche briefing e a IA monta proposta formatada",
        "campos": [
            {"nome": "sua_empresa", "label": "Sua Empresa / Prestador", "tipo": "text", "placeholder": "Nome da sua empresa"},
            {"nome": "cliente", "label": "Nome do Cliente / Empresa", "tipo": "text", "placeholder": "Para quem é a proposta"},
            {"nome": "servico", "label": "Serviço / Solução Oferecida", "tipo": "textarea", "placeholder": "Descreva o que será entregue"},
            {"nome": "valor", "label": "Investimento / Faixa de Valor", "tipo": "text", "placeholder": "Ex: R$ 5.000 ou sob consulta"},
            {"nome": "prazo", "label": "Prazo de Entrega", "tipo": "text", "placeholder": "Ex: 30 dias úteis"},
        ],
        "system_prompt": """Você é especialista em propostas comerciais profissionais.
Prestador: <<sua_empresa>> | Cliente: <<cliente>>
Serviço: <<servico>> | Investimento: <<valor>> | Prazo: <<prazo>>

Monte proposta comercial completa com:
1. CAPA (título, data, para quem)
2. CONTEXTO (problema ou necessidade identificada)
3. SOLUÇÃO PROPOSTA (o que será entregue, como, por que essa abordagem)
4. ESCOPO DETALHADO (entregáveis, etapas, o que está incluso e o que não está)
5. INVESTIMENTO (valor, forma de pagamento, validade da proposta)
6. PRAZO E CRONOGRAMA
7. PRÓXIMOS PASSOS
8. TERMOS GERAIS

Linguagem profissional, orientada a valor, não a custo.""",
    },

    "05_diagnostico_marca": {
        "id": "05_diagnostico_marca",
        "nome": "Diagnóstico de Marca com IA",
        "icone": "🔍",
        "categoria": "Marca",
        "descricao": "Análise automática com recomendações de posicionamento",
        "campos": [
            {"nome": "empresa", "label": "Nome da Empresa / Marca", "tipo": "text", "placeholder": "Nome da empresa"},
            {"nome": "segmento", "label": "Segmento de Mercado", "tipo": "text", "placeholder": "Ex: Saúde e bem-estar, Tecnologia B2B"},
            {"nome": "publico", "label": "Público-Alvo Atual", "tipo": "text", "placeholder": "Quem são seus clientes hoje"},
            {"nome": "diferenciais", "label": "O que Você Acha seu Diferencial", "tipo": "textarea", "placeholder": "O que te faz diferente da concorrência"},
            {"nome": "problemas", "label": "Principais Dificuldades da Marca", "tipo": "textarea", "placeholder": "Onde a marca perde ou tem dificuldade"},
        ],
        "system_prompt": """Você é consultor sênior de branding e posicionamento estratégico.
Empresa: <<empresa>> | Segmento: <<segmento>> | Público: <<publico>>
Diferenciais percebidos: <<diferenciais>>
Dificuldades: <<problemas>>

Faça diagnóstico completo de marca:
1. ANÁLISE DE POSICIONAMENTO ATUAL (como a marca se comunica hoje)
2. PONTOS FORTES identificados
3. PONTOS DE MELHORIA críticos
4. ANÁLISE DE PÚBLICO (está alcançando quem deveria?)
5. OPORTUNIDADES DE POSICIONAMENTO (nichos não explorados)
6. RECOMENDAÇÕES PRÁTICAS (5 ações prioritárias)
7. PRÓXIMO PASSO SUGERIDO

Seja direto e específico. Não genérico.""",
    },

    "06_nomes_marca": {
        "id": "06_nomes_marca",
        "nome": "Gerador de Nomes de Marca ou Produto",
        "icone": "✨",
        "categoria": "Marca",
        "descricao": "IA sugere nomes criativos com base no nicho e arquétipo",
        "campos": [
            {"nome": "segmento", "label": "Segmento / Nicho", "tipo": "text", "placeholder": "Ex: Academia feminina, App de finanças"},
            {"nome": "publico", "label": "Público-Alvo", "tipo": "text", "placeholder": "Ex: Mulheres 30-45 anos"},
            {"nome": "arquetipo", "label": "Arquétipo de Marca", "tipo": "select", "opcoes": ["Herói", "Sábio", "Cuidador", "Criador", "Rebelde", "Explorador", "Amante", "Bobo da Corte", "Mágico", "Governante", "Inocente", "Cidadão Comum"]},
            {"nome": "estilo", "label": "Estilo do Nome", "tipo": "select", "opcoes": ["Moderno e minimalista", "Clássico e sólido", "Divertido e criativo", "Técnico e profissional", "Emocional e humano"]},
            {"nome": "palavras_chave", "label": "Palavras ou Conceitos que Inspiram", "tipo": "text", "placeholder": "Ex: força, leveza, transformação"},
        ],
        "system_prompt": """Você é especialista em naming de marcas e produtos.
Segmento: <<segmento>> | Público: <<publico>>
Arquétipo: <<arquetipo>> | Estilo: <<estilo>>
Inspirações: <<palavras_chave>>

Gere 15 opções de nome organizadas em categorias:

CATEGORIA 1 — NOMES DIRETOS (descritivos, fáceis de entender):
[5 sugestões com explicação de cada]

CATEGORIA 2 — NOMES METAFÓRICOS (evocam sensação ou conceito):
[5 sugestões com explicação de cada]

CATEGORIA 3 — NOMES INVENTADOS / ÚNICOS (neologismos, fusões):
[5 sugestões com explicação de cada]

Para cada nome: significado, por que funciona para este público, disponibilidade (provável/verificar), domínio sugerido.""",
    },

    "07_briefing": {
        "id": "07_briefing",
        "nome": "Assistente de Briefing Automatizado",
        "icone": "📝",
        "categoria": "Documentos",
        "descricao": "Cliente responde perguntas e a IA organiza em briefing estruturado",
        "campos": [
            {"nome": "tipo_projeto", "label": "Tipo de Projeto", "tipo": "select", "opcoes": ["Site/Landing Page", "Identidade Visual", "Campanha de Marketing", "Vídeo/Audiovisual", "Conteúdo/Copywriting", "Consultoria", "Desenvolvimento de Produto", "Outro"]},
            {"nome": "empresa", "label": "Empresa / Cliente", "tipo": "text", "placeholder": "Nome da empresa do cliente"},
            {"nome": "objetivo", "label": "Objetivo Principal do Projeto", "tipo": "textarea", "placeholder": "O que o projeto precisa alcançar?"},
            {"nome": "publico", "label": "Público-Alvo do Projeto", "tipo": "textarea", "placeholder": "Quem vai usar, ver ou receber isso?"},
            {"nome": "referencias", "label": "Referências ou Exemplos", "tipo": "textarea", "placeholder": "Sites, marcas, cores, estilos que gosta ou não gosta"},
            {"nome": "prazo", "label": "Prazo / Entrega Esperada", "tipo": "text", "placeholder": "Ex: 3 semanas, até 15/07"},
        ],
        "system_prompt": """Você é um especialista em gestão de projetos criativos.
Tipo de projeto: <<tipo_projeto>> | Cliente: <<empresa>>
Objetivo: <<objetivo>>
Público: <<publico>>
Referências: <<referencias>>
Prazo: <<prazo>>

Organize um briefing profissional e completo com:
1. RESUMO EXECUTIVO (síntese do projeto em 3 linhas)
2. CONTEXTO E DESAFIO (situação atual e problema a resolver)
3. OBJETIVOS (primários e secundários, mensuráveis se possível)
4. PÚBLICO-ALVO DETALHADO (perfil, dores, comportamentos)
5. ESCOPO DO PROJETO (o que está incluso)
6. REFERÊNCIAS E DIRECIONAMENTO CRIATIVO
7. PRAZO E MARCO DE ENTREGA
8. PERGUNTAS EM ABERTO (informações ainda necessárias)
9. PRÓXIMOS PASSOS RECOMENDADOS""",
    },

    "08_analise_concorrentes": {
        "id": "08_analise_concorrentes",
        "nome": "Análise de Concorrentes com IA",
        "icone": "🔭",
        "categoria": "Marca",
        "descricao": "IA compara posicionamento, diferenciais e pontos fracos",
        "campos": [
            {"nome": "sua_empresa", "label": "Sua Empresa", "tipo": "text", "placeholder": "Nome da sua empresa"},
            {"nome": "segmento", "label": "Segmento / Mercado", "tipo": "text", "placeholder": "Ex: SaaS de RH, Academia premium"},
            {"nome": "concorrentes", "label": "Concorrentes a Analisar", "tipo": "textarea", "placeholder": "Liste os principais concorrentes (separados por vírgula)"},
            {"nome": "foco", "label": "Foco da Análise", "tipo": "select", "opcoes": ["Posicionamento e marca", "Preços e modelo de negócio", "Marketing e conteúdo", "Produto e funcionalidades", "Atendimento ao cliente", "Análise completa"]},
        ],
        "system_prompt": """Você é analista de inteligência competitiva e estratégia de mercado.
Empresa analisada: <<sua_empresa>> | Segmento: <<segmento>>
Concorrentes: <<concorrentes>> | Foco: <<foco>>

Faça análise competitiva completa:
1. MAPA COMPETITIVO (posicionamento de cada player no mercado)
2. TABELA COMPARATIVA (critérios: preço, diferencial, público, canais, pontos fortes, fracos)
3. ANÁLISE DE <<foco>> DETALHADA por concorrente
4. OPORTUNIDADES IDENTIFICADAS (onde há lacuna no mercado)
5. AMEAÇAS A MONITORAR
6. RECOMENDAÇÕES ESTRATÉGICAS para <<sua_empresa>>

Use busca web se necessário para dados atualizados.""",
    },

    "09_faq": {
        "id": "09_faq",
        "nome": "Gerador de FAQ Personalizado",
        "icone": "❓",
        "categoria": "Documentos",
        "descricao": "IA cria perguntas frequentes com base nos serviços do cliente",
        "campos": [
            {"nome": "empresa", "label": "Empresa / Marca", "tipo": "text", "placeholder": "Nome da empresa"},
            {"nome": "servico", "label": "Serviço ou Produto Principal", "tipo": "textarea", "placeholder": "Descreva o que a empresa oferece"},
            {"nome": "publico", "label": "Público-Alvo", "tipo": "text", "placeholder": "Quem são os clientes típicos"},
            {"nome": "duvidas_comuns", "label": "Dúvidas que Clientes Costumam Ter", "tipo": "textarea", "placeholder": "Se souber, liste as dúvidas mais comuns (opcional)"},
        ],
        "system_prompt": """Você é especialista em experiência do cliente e suporte.
Empresa: <<empresa>> | Serviço/Produto: <<servico>> | Público: <<publico>>
Dúvidas relatadas: <<duvidas_comuns>>

Crie FAQ completo e profissional com 20 perguntas e respostas:

SEÇÃO 1 — SOBRE A EMPRESA / SERVIÇO (5 perguntas)
SEÇÃO 2 — COMO FUNCIONA / PROCESSO (5 perguntas)
SEÇÃO 3 — PREÇOS E PAGAMENTO (4 perguntas)
SEÇÃO 4 — GARANTIAS E SUPORTE (3 perguntas)
SEÇÃO 5 — CASOS ESPECIAIS / EDGE CASES (3 perguntas)

Formato: **Pergunta?**
Resposta clara, objetiva e no tom adequado para o público.""",
    },

    "10_copy_campanhas": {
        "id": "10_copy_campanhas",
        "nome": "Assistente de Copy para Campanhas",
        "icone": "📣",
        "categoria": "Vendas",
        "descricao": "IA gera headline, subhead, CTA e corpo de texto para anúncios",
        "campos": [
            {"nome": "produto", "label": "Produto / Serviço", "tipo": "text", "placeholder": "O que está sendo anunciado"},
            {"nome": "publico", "label": "Público-Alvo", "tipo": "text", "placeholder": "Ex: Donos de academia, mães 25-40 anos"},
            {"nome": "beneficio_principal", "label": "Principal Benefício / Transformação", "tipo": "textarea", "placeholder": "O que muda na vida do cliente após usar seu produto"},
            {"nome": "canal", "label": "Canal / Formato", "tipo": "select", "opcoes": ["Google Ads", "Facebook/Instagram Ads", "LinkedIn Ads", "Email marketing", "SMS/WhatsApp", "Landing Page", "Outdoor/Impresso"]},
            {"nome": "objetivo", "label": "Objetivo da Campanha", "tipo": "select", "opcoes": ["Geração de leads", "Vendas diretas", "Awareness de marca", "Retenção / Reengajamento", "Download de material"]},
        ],
        "system_prompt": """Você é copywriter sênior especializado em campanhas de alta conversão.
Produto: <<produto>> | Público: <<publico>>
Benefício: <<beneficio_principal>> | Canal: <<canal>> | Objetivo: <<objetivo>>

Crie 3 variações de copy completo para <<canal>>:

VARIAÇÃO 1 — EMOCIONAL (foca na transformação e desejo):
- Headline:
- Subheadline:
- Corpo:
- CTA:

VARIAÇÃO 2 — RACIONAL (foca em dados, prova, lógica):
- Headline:
- Subheadline:
- Corpo:
- CTA:

VARIAÇÃO 3 — URGÊNCIA/ESCASSEZ:
- Headline:
- Subheadline:
- Corpo:
- CTA:

Inclua sugestão de A/B test mais relevante.""",
    },

    "11_calendario_conteudo": {
        "id": "11_calendario_conteudo",
        "nome": "Calendário de Conteúdo Mensal",
        "icone": "📅",
        "categoria": "Conteúdo",
        "descricao": "30 dias de pautas por pilar estratégico geradas automaticamente",
        "campos": [
            {"nome": "nicho", "label": "Nicho / Segmento", "tipo": "text", "placeholder": "Ex: Nutricionista clínica, Coach de carreira"},
            {"nome": "plataforma", "label": "Plataforma Principal", "tipo": "select", "opcoes": ["Instagram", "LinkedIn", "TikTok", "YouTube", "Blog", "Multi-plataforma"]},
            {"nome": "pilares", "label": "Pilares de Conteúdo", "tipo": "textarea", "placeholder": "Ex: Educação, Bastidores, Depoimentos, Vendas, Motivação"},
            {"nome": "objetivo_mes", "label": "Objetivo do Mês", "tipo": "text", "placeholder": "Ex: Lançar curso, aumentar seguidores, gerar leads"},
            {"nome": "frequencia", "label": "Frequência de Publicação", "tipo": "select", "opcoes": ["Diário", "5x por semana", "3x por semana", "Dias úteis"]},
        ],
        "system_prompt": """Você é estrategista de conteúdo digital para <<plataforma>>.
Nicho: <<nicho>> | Objetivo do mês: <<objetivo_mes>>
Pilares: <<pilares>> | Frequência: <<frequencia>>

Crie calendário editorial de 30 dias:

SEMANA 1 — [tema da semana]:
[dia] — [pilar] — [formato] — [tema/pauta específica] — [gancho sugerido]
... (um por dia conforme frequência)

SEMANA 2 — [tema]:
...

SEMANA 3 — [tema]:
...

SEMANA 4 — [tema / foco em objetivo do mês]:
...

Ao final: 5 ideias de destaque para reels/shorts e 3 CTAs estratégicos para o mês.""",
    },

    "12_icp": {
        "id": "12_icp",
        "nome": "Ferramenta de ICP com IA",
        "icone": "🎯",
        "categoria": "Marca",
        "descricao": "IA define cliente ideal com base em dados do negócio",
        "campos": [
            {"nome": "produto", "label": "Produto / Serviço Oferecido", "tipo": "textarea", "placeholder": "O que você vende e como funciona"},
            {"nome": "mercado", "label": "Mercado / Setor", "tipo": "text", "placeholder": "Ex: B2B SaaS, Varejo físico, Serviços profissionais"},
            {"nome": "problema_que_resolve", "label": "Problema que Você Resolve", "tipo": "textarea", "placeholder": "Qual dor ou problema o seu produto soluciona"},
            {"nome": "ticket_medio", "label": "Ticket Médio / Faixa de Preço", "tipo": "text", "placeholder": "Ex: R$ 500/mês, R$ 2.000 a R$ 10.000"},
            {"nome": "melhores_clientes", "label": "Características dos Seus Melhores Clientes", "tipo": "textarea", "placeholder": "Se já tem clientes, o que eles têm em comum?"},
        ],
        "system_prompt": """Você é especialista em estratégia de go-to-market e definição de ICP.
Produto/Serviço: <<produto>> | Mercado: <<mercado>>
Problema resolvido: <<problema_que_resolve>> | Ticket: <<ticket_medio>>
Melhores clientes atuais: <<melhores_clientes>>

Monte o ICP (Ideal Customer Profile) completo:

1. PERFIL DEMOGRÁFICO
   - Cargo / Posição (B2B) ou Perfil pessoal (B2C)
   - Faixa etária, localização, renda/faturamento

2. PERFIL PSICOGRÁFICO
   - Valores, crenças, estilo de vida
   - Fontes de informação que consome

3. DOR PRINCIPAL (o que tira o sono)
4. DESEJO PRINCIPAL (transformação desejada)
5. OBJEÇÕES TÍPICAS antes de comprar
6. JORNADA DE COMPRA (como descobre, avalia, decide)
7. MENSAGEM QUE RESSOA (como falar com ele)
8. CANAIS PARA ALCANÇÁ-LO""",
    },

    "13_chatbot_clinica": {
        "id": "13_chatbot_clinica",
        "nome": "Chatbot de Triagem para Clínicas",
        "icone": "🏥",
        "categoria": "Atendimento",
        "descricao": "Assistente que coleta sintomas, histórico e agenda consulta",
        "campos": [
            {"nome": "clinica", "label": "Nome da Clínica", "tipo": "text", "placeholder": "Ex: Clínica São Lucas"},
            {"nome": "especialidade", "label": "Especialidade(s) Médica(s)", "tipo": "text", "placeholder": "Ex: Clínica geral, Dermatologia, Ortopedia"},
            {"nome": "servicos", "label": "Serviços Oferecidos", "tipo": "textarea", "placeholder": "Liste os procedimentos e serviços disponíveis"},
            {"nome": "horarios", "label": "Horários de Atendimento", "tipo": "text", "placeholder": "Ex: Seg-Sex 8h-18h, Sáb 8h-12h"},
        ],
        "system_prompt": """Você é especialista em fluxos de atendimento para clínicas de saúde.
Clínica: <<clinica>> | Especialidade: <<especialidade>>
Serviços: <<servicos>> | Horários: <<horarios>>

Crie o script completo do chatbot de triagem com:
1. SAUDAÇÃO E IDENTIFICAÇÃO DO PACIENTE
2. TRIAGEM DE URGÊNCIA (algoritmo para identificar casos urgentes)
3. COLETA DE SINTOMAS (perguntas por especialidade)
4. HISTÓRICO BÁSICO (alergias, medicamentos em uso, última consulta)
5. AGENDAMENTO (disponibilidade, convênio ou particular)
6. CONFIRMAÇÃO E INSTRUÇÕES (o que trazer, preparo necessário)
7. ENCERRAMENTO

Inclua mensagens para casos de emergência (direcionar para UPA/SAMU).""",
    },

    "14_descricao_produto": {
        "id": "14_descricao_produto",
        "nome": "Gerador de Descrições de Produto",
        "icone": "🛍️",
        "categoria": "Vendas",
        "descricao": "IA escreve descrições persuasivas para e-commerce ou catálogo",
        "campos": [
            {"nome": "produto", "label": "Nome do Produto", "tipo": "text", "placeholder": "Nome exato do produto"},
            {"nome": "categoria", "label": "Categoria do Produto", "tipo": "text", "placeholder": "Ex: Suplemento, Roupa fitness, Eletrônico"},
            {"nome": "beneficios", "label": "Principais Benefícios / Características", "tipo": "textarea", "placeholder": "O que este produto faz, seus diferenciais e specs técnicos"},
            {"nome": "publico", "label": "Público-Alvo", "tipo": "text", "placeholder": "Para quem é este produto"},
            {"nome": "tom", "label": "Tom de Comunicação", "tipo": "select", "opcoes": ["Técnico e informativo", "Emocional e aspiracional", "Descontraído e jovem", "Premium e sofisticado", "Natural e acessível"]},
        ],
        "system_prompt": """Você é copywriter especializado em descrições de produto para e-commerce e catálogos.
Produto: <<produto>> | Categoria: <<categoria>> | Tom: <<tom>>
Benefícios: <<beneficios>> | Público: <<publico>>

Escreva 3 variações de descrição:

VERSÃO CURTA (para card/listagem — até 80 palavras):
[descrição + benefício principal + CTA implícito]

VERSÃO MÉDIA (para página de produto — 150-200 palavras):
[gancho emocional] + [o que é] + [benefícios em lista] + [para quem] + [CTA]

VERSÃO LONGA SEO (completa para página — 300+ palavras):
[headline] + [problema que resolve] + [benefícios detalhados] + [especificações] + [para quem é ideal] + [não é para quem] + [CTA forte]

Inclua 5 bullet points de benefícios formatados para e-commerce.""",
    },

    "15_newsletter": {
        "id": "15_newsletter",
        "nome": "Assistente de Criação de Newsletter",
        "icone": "📧",
        "categoria": "Conteúdo",
        "descricao": "IA monta newsletter completa com base em tema e audiência",
        "campos": [
            {"nome": "tema", "label": "Tema Principal desta Edição", "tipo": "textarea", "placeholder": "Sobre o que será esta newsletter"},
            {"nome": "audiencia", "label": "Audiência / Perfil dos Assinantes", "tipo": "text", "placeholder": "Ex: Empreendedores digitais, Profissionais de RH"},
            {"nome": "tom", "label": "Tom de Voz", "tipo": "select", "opcoes": ["Formal e profissional", "Casual e próximo", "Educativo e informativo", "Inspirador", "Direto e prático"]},
            {"nome": "secoes", "label": "Seções Desejadas", "tipo": "text", "placeholder": "Ex: Abertura, Artigo principal, Dica rápida, Recomendação, Encerramento"},
        ],
        "system_prompt": """Você é especialista em email marketing e newsletters de alta taxa de abertura.
Tema: <<tema>> | Audiência: <<audiencia>> | Tom: <<tom>>
Seções: <<secoes>>

Monte newsletter completa e pronta para envio:

ASSUNTO DO EMAIL (3 opções ranqueadas por potencial de abertura):
1. [assunto com curiosidade/benefício]
2. [assunto direto]
3. [assunto personalizado/íntimo]

PRÉ-HEADER: [texto do preheader — complementa o assunto]

--- CONTEÚDO ---

[Estruture as seções: <<secoes>>]

Para cada seção: título, conteúdo, CTA se relevante.

--- RODAPÉ ---
[Links essenciais + descadastro]

Estime taxa de leitura esperada e melhor horário de envio para este perfil.""",
    },

    "16_revisao_texto": {
        "id": "16_revisao_texto",
        "nome": "Revisão e Reescrita de Textos",
        "icone": "✏️",
        "categoria": "Documentos",
        "descricao": "IA corrige, adapta tom e otimiza textos do cliente",
        "campos": [
            {"nome": "texto", "label": "Texto Original", "tipo": "textarea", "placeholder": "Cole aqui o texto que deseja revisar ou reescrever"},
            {"nome": "objetivo", "label": "Objetivo do Texto", "tipo": "text", "placeholder": "Ex: Post de blog, proposta, email, post de Instagram"},
            {"nome": "tom_desejado", "label": "Tom de Voz Desejado", "tipo": "select", "opcoes": ["Formal e profissional", "Casual e descontraído", "Persuasivo e vendas", "Técnico e preciso", "Acolhedor e empático", "Inspirador"]},
            {"nome": "ajustes", "label": "Ajustes Específicos Desejados", "tipo": "textarea", "placeholder": "Ex: Deixar mais curto, melhorar o gancho, adicionar CTA, corrigir erros"},
        ],
        "system_prompt": """Você é editor e revisor profissional de textos em português brasileiro.
Objetivo do texto: <<objetivo>> | Tom desejado: <<tom_desejado>>
Ajustes solicitados: <<ajustes>>

Texto original:
---
<<texto>>
---

Entregue:
1. DIAGNÓSTICO (problemas encontrados: clareza, tom, estrutura, gramática)
2. TEXTO REVISADO (mantendo intenção original com melhorias)
3. TEXTO REESCRITO (versão mais otimizada com tom <<tom_desejado>>)
4. HIGHLIGHTS DAS PRINCIPAIS MUDANÇAS (o que mudou e por quê)
5. SUGESTÕES ADICIONAIS (melhorias opcionais)""",
    },

    "17_pitch_deck": {
        "id": "17_pitch_deck",
        "nome": "Gerador de Pitch Deck com IA",
        "icone": "🚀",
        "categoria": "Vendas",
        "descricao": "IA estrutura apresentação comercial com base em dados do negócio",
        "campos": [
            {"nome": "empresa", "label": "Nome da Empresa / Startup", "tipo": "text", "placeholder": "Nome da empresa"},
            {"nome": "problema", "label": "Problema que Resolve", "tipo": "textarea", "placeholder": "Qual problema do mercado você resolve"},
            {"nome": "solucao", "label": "Sua Solução", "tipo": "textarea", "placeholder": "Como você resolve esse problema"},
            {"nome": "mercado", "label": "Tamanho do Mercado (TAM/SAM/SOM)", "tipo": "text", "placeholder": "Ex: Mercado de R$ 5bi, nossa fatia inicial de R$ 50mi"},
            {"nome": "modelo_negocio", "label": "Modelo de Negócio / Como Monetiza", "tipo": "text", "placeholder": "Ex: SaaS R$ 299/mês, comissão 10%, venda direta"},
            {"nome": "objetivo_pitch", "label": "Objetivo do Pitch", "tipo": "select", "opcoes": ["Captação de investimento", "Parceria comercial", "Cliente enterprise", "Aceleração/Incubação"]},
        ],
        "system_prompt": """Você é especialista em pitches para investidores e parceiros estratégicos.
Empresa: <<empresa>> | Objetivo: <<objetivo_pitch>>
Problema: <<problema>> | Solução: <<solucao>>
Mercado: <<mercado>> | Modelo de negócio: <<modelo_negocio>>

Estruture o pitch deck completo (slide a slide):

SLIDE 1 — CAPA: [título, tagline de uma linha]
SLIDE 2 — PROBLEMA: [dor do mercado com dado/stat impactante]
SLIDE 3 — SOLUÇÃO: [como resolve, benefícios principais]
SLIDE 4 — PRODUTO/DEMO: [o que mostrar, printscreen sugerido]
SLIDE 5 — MERCADO: [TAM/SAM/SOM com justificativa]
SLIDE 6 — MODELO DE NEGÓCIO: [como ganha dinheiro, unit economics]
SLIDE 7 — TRAÇÃO: [métricas atuais, clientes, MRR, crescimento]
SLIDE 8 — CONCORRÊNCIA: [mapa competitivo, seu diferencial]
SLIDE 9 — GO-TO-MARKET: [estratégia de aquisição e crescimento]
SLIDE 10 — TIME: [quem são os fundadores e por que eles]
SLIDE 11 — FINANCEIRO: [projeções 3 anos, uso do investimento]
SLIDE 12 — CTA: [o que você quer — valor, equity, próximo passo]

Para cada slide: título, bullet points de conteúdo, sugestão visual.""",
    },

    "18_seo": {
        "id": "18_seo",
        "nome": "Assistente de SEO com IA",
        "icone": "🔎",
        "categoria": "Conteúdo",
        "descricao": "IA sugere palavras-chave, títulos e meta descriptions otimizados",
        "campos": [
            {"nome": "pagina", "label": "Tema ou URL da Página", "tipo": "text", "placeholder": "Ex: Página sobre consultoria financeira, /blog/investimentos"},
            {"nome": "palavra_chave", "label": "Palavra-Chave Principal", "tipo": "text", "placeholder": "Ex: consultoria financeira para MEI"},
            {"nome": "publico", "label": "Público que Você Quer Atrair", "tipo": "text", "placeholder": "Ex: MEIs buscando declaração de IR"},
            {"nome": "concorrentes_seo", "label": "Concorrentes Que Aparecem Bem no Google", "tipo": "text", "placeholder": "Sites concorrentes nas buscas (opcional)"},
        ],
        "system_prompt": """Você é especialista em SEO para Google, focado em resultados orgânicos.
Tema da página: <<pagina>> | Palavra-chave principal: <<palavra_chave>>
Público-alvo: <<publico>> | Concorrentes: <<concorrentes_seo>>

Entregue análise e recomendações SEO completas:

1. PALAVRAS-CHAVE
   - Principal: <<palavra_chave>>
   - Secundárias (8-10 variações de cauda longa)
   - Intenção de busca (informacional/navegacional/transacional)

2. TITLE TAG (3 opções com até 60 caracteres)

3. META DESCRIPTION (3 opções com até 155 caracteres + CTA)

4. ESTRUTURA DE CONTEÚDO SUGERIDA
   - H1, H2s, H3s recomendados
   - Perguntas para incluir (People Also Ask)

5. LINK INTERNO E EXTERNO (sugestões estratégicas)

6. SNIPPET RICO (schema markup recomendado)

7. QUICK WINS (o que implementar primeiro para ranquear mais rápido)

Use web_search para pesquisar volume de busca estimado das keywords.""",
    },

    "19_email_personalizado": {
        "id": "19_email_personalizado",
        "nome": "Personalização de E-mail com IA",
        "icone": "💌",
        "categoria": "Vendas",
        "descricao": "IA adapta corpo do e-mail para cada segmento da base",
        "campos": [
            {"nome": "produto", "label": "Produto / Serviço sendo Promovido", "tipo": "text", "placeholder": "O que está sendo oferecido no email"},
            {"nome": "segmentos", "label": "Segmentos da Base", "tipo": "textarea", "placeholder": "Ex: Leads novos, Clientes ativos, Inativos há 90 dias, Compradores VIP"},
            {"nome": "objetivo", "label": "Objetivo do Email", "tipo": "select", "opcoes": ["Venda direta", "Reengajamento", "Nutrição de lead", "Boas-vindas", "Upsell/Cross-sell", "Recuperação de carrinho"]},
            {"nome": "tom", "label": "Tom de Voz", "tipo": "select", "opcoes": ["Formal", "Amigável", "Urgente", "Exclusivo/Premium", "Casual"]},
        ],
        "system_prompt": """Você é especialista em email marketing e automação de comunicação.
Produto: <<produto>> | Objetivo: <<objetivo>> | Tom: <<tom>>
Segmentos da base: <<segmentos>>

Para cada segmento listado em <<segmentos>>, escreva um email personalizado completo:

[SEGMENTO: nome do segmento]
ASSUNTO: [3 opções]
PREHEADER:
---
Corpo do email:
[Saudação personalizada]
[Conteúdo específico para este segmento — dor/interesse/histórico]
[Oferta/Mensagem principal]
[CTA]
[Assinatura]
---
Melhor horário de envio para este segmento:
Taxa de abertura esperada:

Repita para cada segmento.""",
    },

    "20_contrato": {
        "id": "20_contrato",
        "nome": "Gerador de Contratos Simples",
        "icone": "📜",
        "categoria": "Documentos",
        "descricao": "IA monta contrato de prestação de serviço com base em inputs",
        "campos": [
            {"nome": "tipo_servico", "label": "Tipo de Serviço", "tipo": "text", "placeholder": "Ex: Desenvolvimento de site, Consultoria de marketing, Design gráfico"},
            {"nome": "contratante", "label": "Contratante (Quem Paga)", "tipo": "text", "placeholder": "Nome / empresa do contratante"},
            {"nome": "contratado", "label": "Contratado (Quem Executa)", "tipo": "text", "placeholder": "Nome / empresa do prestador"},
            {"nome": "valor", "label": "Valor e Forma de Pagamento", "tipo": "text", "placeholder": "Ex: R$ 5.000 em 2x — 50% início, 50% entrega"},
            {"nome": "prazo", "label": "Prazo de Execução", "tipo": "text", "placeholder": "Ex: 30 dias corridos após aprovação do briefing"},
            {"nome": "escopo", "label": "Escopo / O Que Está Incluso", "tipo": "textarea", "placeholder": "Descreva o que será entregue"},
        ],
        "system_prompt": """Você é especialista em contratos de prestação de serviços para profissionais e pequenas empresas.
Tipo de serviço: <<tipo_servico>>
Contratante: <<contratante>> | Contratado: <<contratado>>
Valor: <<valor>> | Prazo: <<prazo>>
Escopo: <<escopo>>

Gere contrato de prestação de serviços completo com:
1. QUALIFICAÇÃO DAS PARTES
2. OBJETO DO CONTRATO (escopo detalhado)
3. PRAZO DE EXECUÇÃO
4. VALOR E FORMA DE PAGAMENTO
5. OBRIGAÇÕES DO CONTRATADO
6. OBRIGAÇÕES DO CONTRATANTE
7. DIREITOS AUTORAIS E PROPRIEDADE INTELECTUAL
8. SIGILO E CONFIDENCIALIDADE
9. RESCISÃO (condições e multas)
10. DISPOSIÇÕES GERAIS (foro, lei aplicável)
11. ASSINATURA

Nota: este é um modelo de referência. Recomende revisão jurídica profissional.""",
    },

    "21_analise_documento": {
        "id": "21_analise_documento",
        "nome": "Análise de Documentos com IA",
        "icone": "📄",
        "categoria": "Documentos",
        "descricao": "IA resume, extrai pontos-chave e interpreta PDFs e contratos",
        "campos": [
            {"nome": "texto_documento", "label": "Texto do Documento", "tipo": "textarea", "placeholder": "Cole aqui o texto do documento, contrato ou PDF para análise"},
            {"nome": "tipo_documento", "label": "Tipo de Documento", "tipo": "select", "opcoes": ["Contrato", "Relatório financeiro", "Proposta comercial", "Documento jurídico", "Artigo / Pesquisa", "E-mail / Comunicado", "Outro"]},
            {"nome": "foco_analise", "label": "Foco da Análise", "tipo": "select", "opcoes": ["Resumo executivo", "Riscos e cláusulas críticas", "Pontos de atenção", "Extração de dados-chave", "Análise completa"]},
        ],
        "system_prompt": """Você é analista especializado em interpretação e síntese de documentos empresariais.
Tipo de documento: <<tipo_documento>> | Foco: <<foco_analise>>

Documento para análise:
---
<<texto_documento>>
---

Entregue análise completa com foco em <<foco_analise>>:

1. RESUMO EXECUTIVO (síntese em até 5 linhas)
2. PONTOS-CHAVE (os 5-7 itens mais importantes)
3. ANÁLISE DE <<foco_analise>> detalhada
4. ALERTAS E PONTOS DE ATENÇÃO (o que precisa de cuidado)
5. PERGUNTAS QUE ESTE DOCUMENTO LEVANTA
6. RECOMENDAÇÃO DE PRÓXIMO PASSO""",
    },

    "22_feedback_alunos": {
        "id": "22_feedback_alunos",
        "nome": "Feedback Automatizado para Alunos",
        "icone": "🎓",
        "categoria": "Educação",
        "descricao": "IA analisa trabalho e devolve feedback estruturado e personalizado",
        "campos": [
            {"nome": "disciplina", "label": "Disciplina / Área", "tipo": "text", "placeholder": "Ex: Redação, Cálculo, Marketing Digital, Programação"},
            {"nome": "nivel", "label": "Nível do Aluno", "tipo": "select", "opcoes": ["Fundamental", "Médio", "Superior", "Pós-graduação", "Profissional / Curso livre"]},
            {"nome": "trabalho_aluno", "label": "Trabalho / Resposta do Aluno", "tipo": "textarea", "placeholder": "Cole aqui o trabalho, redação, código ou resposta do aluno"},
            {"nome": "criterios", "label": "Critérios de Avaliação", "tipo": "textarea", "placeholder": "Ex: Clareza, Argumentação, Gramática, Originalidade (0-10 cada)"},
            {"nome": "tom_feedback", "label": "Tom do Feedback", "tipo": "select", "opcoes": ["Encorajador e construtivo", "Técnico e objetivo", "Desafiador e rigoroso", "Gentil e motivador"]},
        ],
        "system_prompt": """Você é educador experiente especializado em feedback pedagógico de alta qualidade.
Disciplina: <<disciplina>> | Nível: <<nivel>> | Tom: <<tom_feedback>>
Critérios: <<criterios>>

Trabalho do aluno:
---
<<trabalho_aluno>>
---

Produza feedback completo e personalizado:

1. AVALIAÇÃO GERAL (nota/conceito + parecer de uma linha)
2. PONTOS FORTES (o que o aluno fez bem — seja específico)
3. PONTOS DE MELHORIA (o que precisa desenvolver — com exemplos)
4. AVALIAÇÃO POR CRITÉRIO (note cada critério de <<criterios>>)
5. COMO MELHORAR (sugestões práticas e concretas)
6. PRÓXIMO PASSO RECOMENDADO (exercício, leitura, revisão)
7. MENSAGEM MOTIVACIONAL (adequada ao nível e tom <<tom_feedback>>)""",
    },

    "23_script_vendas": {
        "id": "23_script_vendas",
        "nome": "Gerador de Scripts de Vendas",
        "icone": "💼",
        "categoria": "Vendas",
        "descricao": "IA cria roteiro de abordagem por etapa do funil e persona",
        "campos": [
            {"nome": "produto", "label": "Produto / Serviço", "tipo": "text", "placeholder": "O que está sendo vendido"},
            {"nome": "persona", "label": "Persona / Perfil do Comprador", "tipo": "text", "placeholder": "Ex: Dono de academia de pequeno porte, Gerente de RH"},
            {"nome": "etapa_funil", "label": "Etapa do Funil", "tipo": "select", "opcoes": ["Prospecção (primeiro contato)", "Qualificação (entender fit)", "Apresentação / Demo", "Proposta e negociação", "Follow-up pós-reunião", "Fechamento", "Reativação de lead frio"]},
            {"nome": "canal", "label": "Canal de Venda", "tipo": "select", "opcoes": ["WhatsApp", "Email", "Ligação telefônica", "Reunião presencial", "Videochamada", "LinkedIn"]},
            {"nome": "objecoes", "label": "Principais Objeções que Enfrenta", "tipo": "textarea", "placeholder": "Ex: Muito caro, preciso pensar, já tenho fornecedor"},
        ],
        "system_prompt": """Você é coach de vendas sênior especializado em processos comerciais B2B e B2C.
Produto: <<produto>> | Persona: <<persona>>
Etapa: <<etapa_funil>> | Canal: <<canal>>
Objeções comuns: <<objecoes>>

Crie script de vendas completo para <<canal>> na etapa <<etapa_funil>>:

1. ABERTURA (como iniciar o contato sem parecer invasivo)
2. QUEBRA-GELO (rapport rápido adequado ao canal)
3. QUALIFICAÇÃO (perguntas para entender a situação)
4. APRESENTAÇÃO DO VALOR (não do produto — da transformação)
5. MANEJO DE OBJEÇÕES para cada objeção listada:
   - Objeção: [...]
   - Resposta: [técnica de contorno com empatia]
   - Retomada: [como voltar à trilha de fechamento]
6. FECHAMENTO (3 técnicas para este perfil)
7. FOLLOW-UP (mensagem para enviar após o contato)

Inclua variações para cada resposta possível do lead.""",
    },

    "24_atendimento_ecommerce": {
        "id": "24_atendimento_ecommerce",
        "nome": "Atendimento para E-commerce",
        "icone": "🛒",
        "categoria": "Atendimento",
        "descricao": "IA responde sobre pedidos, prazo, troca e dúvidas de produto",
        "campos": [
            {"nome": "loja", "label": "Nome da Loja", "tipo": "text", "placeholder": "Nome do e-commerce"},
            {"nome": "produtos", "label": "Categorias de Produtos", "tipo": "text", "placeholder": "Ex: Moda feminina, Eletrônicos, Suplementos"},
            {"nome": "prazo_entrega", "label": "Prazo Médio de Entrega", "tipo": "text", "placeholder": "Ex: 5-10 dias úteis"},
            {"nome": "politica_devolucao", "label": "Política de Devolução/Troca", "tipo": "textarea", "placeholder": "Descreva as regras de troca, devolução e prazo"},
            {"nome": "canais_suporte", "label": "Canais de Suporte Disponíveis", "tipo": "text", "placeholder": "Ex: WhatsApp, email, chat no site"},
        ],
        "system_prompt": """Você é especialista em customer service para e-commerce.
Loja: <<loja>> | Produtos: <<produtos>>
Prazo de entrega: <<prazo_entrega>> | Canais: <<canais_suporte>>
Política de devolução: <<politica_devolucao>>

Crie kit completo de atendimento ao cliente para <<loja>>:

1. RESPOSTAS PADRÃO (templates para os 15 atendimentos mais comuns):
   - Rastrear pedido / Status de entrega
   - Produto não chegou no prazo
   - Produto com defeito
   - Solicitação de troca
   - Cancelamento de pedido
   - Produto diferente do anunciado
   - Dúvida sobre tamanho/especificação
   - [+ 8 situações comuns para <<produtos>>]

2. FLUXO DE ESCALAÇÃO (quando e como escalar para humano)
3. RESPOSTAS PARA AVALIAÇÃO NEGATIVA (como responder 1-2 estrelas)
4. MENSAGENS PROATIVAS (pós-venda, confirmação, entrega)

Formato: tom amigável e prestativo, linguagem clara.""",
    },

    "25_painel_conteudo": {
        "id": "25_painel_conteudo",
        "nome": "Painel de Gestão de Conteúdo IA",
        "icone": "🎛️",
        "categoria": "Gestão",
        "descricao": "Hub estratégico: planejamento e organização de todo o conteúdo da equipe",
        "campos": [
            {"nome": "empresa", "label": "Empresa / Marca", "tipo": "text", "placeholder": "Nome da empresa"},
            {"nome": "equipe", "label": "Tamanho e Perfil da Equipe de Conteúdo", "tipo": "text", "placeholder": "Ex: 2 redatores + 1 designer, freelancers"},
            {"nome": "canais_ativos", "label": "Canais de Conteúdo Ativos", "tipo": "text", "placeholder": "Ex: Instagram, Blog, Newsletter, YouTube"},
            {"nome": "objetivos_mensais", "label": "Objetivos e Metas do Mês", "tipo": "textarea", "placeholder": "Ex: Publicar 30 posts, lançar campanha X, atingir Y seguidores"},
            {"nome": "desafios", "label": "Principais Desafios da Equipe", "tipo": "textarea", "placeholder": "Ex: Falta de pauta, conteúdo repetitivo, baixo engajamento"},
        ],
        "system_prompt": """Você é diretor de conteúdo e estrategista de marketing digital.
Empresa: <<empresa>> | Equipe: <<equipe>>
Canais: <<canais_ativos>> | Objetivos do mês: <<objetivos_mensais>>
Desafios: <<desafios>>

Monte painel estratégico completo de gestão de conteúdo:

1. DIAGNÓSTICO ATUAL (avaliação dos canais e desafios)

2. PLANO DE CONTEÚDO DO MÊS
   - Objetivos SMART
   - Distribuição de publicações por canal
   - Pilares e temas prioritários

3. FLUXO DE TRABALHO DA EQUIPE
   - Processo de produção (briefing → criação → revisão → publicação)
   - Distribuição de tarefas por perfil
   - Prazos sugeridos

4. MÉTRICAS DE ACOMPANHAMENTO (KPIs por canal)

5. BANCO DE PAUTAS (20 ideias de conteúdo para os canais ativos)

6. FERRAMENTAS RECOMENDADAS (para cada etapa do processo)

7. PRÓXIMAS AÇÕES PRIORITÁRIAS (lista de tarefas imediatas)""",
    },
}


def list_templates() -> list[dict]:
    return [
        {k: v for k, v in t.items() if k != "system_prompt"}
        for t in TEMPLATES.values()
    ]


def get_template(template_id: str) -> dict | None:
    return TEMPLATES.get(template_id)


def build_task(template_id: str, inputs: dict) -> str | None:
    """Build final task string with injected template context."""
    tmpl = TEMPLATES.get(template_id)
    if not tmpl:
        return None
    ctx = _fmt(tmpl["system_prompt"], inputs)
    campos_map = {c["nome"]: c["label"] for c in tmpl["campos"]}
    inputs_str = "\n".join(
        f"- {campos_map.get(k, k)}: {v}"
        for k, v in inputs.items() if v and v.strip()
    )
    return (
        f"[FERRAMENTA: {tmpl['nome']}]\n\n"
        f"{ctx}\n\n"
        f"PARÂMETROS FORNECIDOS:\n{inputs_str}\n\n"
        f"Execute a tarefa acima de forma completa, estruturada e de alta qualidade. "
        f"Siga exatamente a estrutura indicada no system prompt."
    )
