export interface TemplateCampo {
  nome: string
  label: string
  tipo: 'text' | 'textarea' | 'select'
  placeholder?: string
  opcoes?: string[]
}

export interface Template {
  id: string
  nome: string
  icone: string
  categoria: string
  descricao: string
  campos: TemplateCampo[]
}

export const TEMPLATES: Template[] = [
  {
    id: '01_roteiro_video',
    nome: 'Gerador de Roteiros de Vídeo',
    icone: '🎬',
    categoria: 'Conteúdo',
    descricao: 'Roteiros personalizados por especialidade e tom de voz',
    campos: [
      { nome: 'especialidade', label: 'Especialidade / Nicho', tipo: 'text', placeholder: 'Ex: Nutrição, Marketing Digital, Finanças' },
      { nome: 'tom', label: 'Tom de Voz', tipo: 'select', opcoes: ['Profissional', 'Descontraído', 'Educativo', 'Inspirador', 'Humorístico'] },
      { nome: 'duracao', label: 'Duração do Vídeo', tipo: 'select', opcoes: ['30 segundos', '1 minuto', '3 minutos', '5 minutos', '10 minutos'] },
      { nome: 'tema', label: 'Tema / Assunto do Vídeo', tipo: 'textarea', placeholder: 'Descreva o assunto principal do vídeo' },
    ],
  },
  {
    id: '02_chatbot_atendimento',
    nome: 'Chatbot de Atendimento para Site',
    icone: '💬',
    categoria: 'Atendimento',
    descricao: 'Assistente que responde dúvidas, faz triagem e captura leads',
    campos: [
      { nome: 'empresa', label: 'Nome da Empresa', tipo: 'text', placeholder: 'Ex: Clínica Vida Plena' },
      { nome: 'segmento', label: 'Segmento / Setor', tipo: 'text', placeholder: 'Ex: Clínica médica, E-commerce, Consultoria' },
      { nome: 'servicos', label: 'Principais Serviços / Produtos', tipo: 'textarea', placeholder: 'Liste os principais serviços ou produtos oferecidos' },
      { nome: 'tom', label: 'Tom do Atendimento', tipo: 'select', opcoes: ['Formal', 'Amigável', 'Neutro', 'Descontraído'] },
    ],
  },
  {
    id: '03_legendas_redes',
    nome: 'Gerador de Legendas para Redes Sociais',
    icone: '📱',
    categoria: 'Conteúdo',
    descricao: 'IA produz legenda, CTA e hashtags a partir de tema ou roteiro',
    campos: [
      { nome: 'plataforma', label: 'Plataforma', tipo: 'select', opcoes: ['Instagram', 'LinkedIn', 'TikTok', 'Facebook', 'Twitter/X', 'YouTube'] },
      { nome: 'tema', label: 'Tema ou Resumo do Conteúdo', tipo: 'textarea', placeholder: 'Sobre o que é o post/vídeo?' },
      { nome: 'tom', label: 'Tom de Voz', tipo: 'select', opcoes: ['Inspirador', 'Educativo', 'Humorístico', 'Provocativo', 'Vendas', 'Storytelling'] },
      { nome: 'objetivo', label: 'Objetivo do Post', tipo: 'select', opcoes: ['Engajamento', 'Vendas', 'Seguidores', 'Tráfego para site', 'Autoridade'] },
    ],
  },
  {
    id: '04_proposta_comercial',
    nome: 'Gerador de Propostas Comerciais',
    icone: '📋',
    categoria: 'Vendas',
    descricao: 'Cliente preenche briefing e a IA monta proposta formatada',
    campos: [
      { nome: 'sua_empresa', label: 'Sua Empresa / Prestador', tipo: 'text', placeholder: 'Nome da sua empresa' },
      { nome: 'cliente', label: 'Nome do Cliente / Empresa', tipo: 'text', placeholder: 'Para quem é a proposta' },
      { nome: 'servico', label: 'Serviço / Solução Oferecida', tipo: 'textarea', placeholder: 'Descreva o que será entregue' },
      { nome: 'valor', label: 'Investimento / Faixa de Valor', tipo: 'text', placeholder: 'Ex: R$ 5.000 ou sob consulta' },
      { nome: 'prazo', label: 'Prazo de Entrega', tipo: 'text', placeholder: 'Ex: 30 dias úteis' },
    ],
  },
  {
    id: '05_diagnostico_marca',
    nome: 'Diagnóstico de Marca com IA',
    icone: '🔍',
    categoria: 'Marca',
    descricao: 'Análise automática com recomendações de posicionamento',
    campos: [
      { nome: 'empresa', label: 'Nome da Empresa / Marca', tipo: 'text', placeholder: 'Nome da empresa' },
      { nome: 'segmento', label: 'Segmento de Mercado', tipo: 'text', placeholder: 'Ex: Saúde e bem-estar, Tecnologia B2B' },
      { nome: 'publico', label: 'Público-Alvo Atual', tipo: 'text', placeholder: 'Quem são seus clientes hoje' },
      { nome: 'diferenciais', label: 'O que Você Acha seu Diferencial', tipo: 'textarea', placeholder: 'O que te faz diferente da concorrência' },
      { nome: 'problemas', label: 'Principais Dificuldades da Marca', tipo: 'textarea', placeholder: 'Onde a marca perde ou tem dificuldade' },
    ],
  },
  {
    id: '06_nomes_marca',
    nome: 'Gerador de Nomes de Marca ou Produto',
    icone: '✨',
    categoria: 'Marca',
    descricao: 'IA sugere nomes criativos com base no nicho e arquétipo',
    campos: [
      { nome: 'segmento', label: 'Segmento / Nicho', tipo: 'text', placeholder: 'Ex: Academia feminina, App de finanças' },
      { nome: 'publico', label: 'Público-Alvo', tipo: 'text', placeholder: 'Ex: Mulheres 30-45 anos' },
      { nome: 'arquetipo', label: 'Arquétipo de Marca', tipo: 'select', opcoes: ['Herói', 'Sábio', 'Cuidador', 'Criador', 'Rebelde', 'Explorador', 'Amante', 'Mágico', 'Governante', 'Inocente'] },
      { nome: 'estilo', label: 'Estilo do Nome', tipo: 'select', opcoes: ['Moderno e minimalista', 'Clássico e sólido', 'Divertido e criativo', 'Técnico e profissional', 'Emocional e humano'] },
      { nome: 'palavras_chave', label: 'Palavras ou Conceitos que Inspiram', tipo: 'text', placeholder: 'Ex: força, leveza, transformação' },
    ],
  },
  {
    id: '07_briefing',
    nome: 'Assistente de Briefing Automatizado',
    icone: '📝',
    categoria: 'Documentos',
    descricao: 'Cliente responde perguntas e a IA organiza em briefing estruturado',
    campos: [
      { nome: 'tipo_projeto', label: 'Tipo de Projeto', tipo: 'select', opcoes: ['Site/Landing Page', 'Identidade Visual', 'Campanha de Marketing', 'Vídeo/Audiovisual', 'Conteúdo/Copywriting', 'Consultoria', 'Outro'] },
      { nome: 'empresa', label: 'Empresa / Cliente', tipo: 'text', placeholder: 'Nome da empresa do cliente' },
      { nome: 'objetivo', label: 'Objetivo Principal do Projeto', tipo: 'textarea', placeholder: 'O que o projeto precisa alcançar?' },
      { nome: 'publico', label: 'Público-Alvo do Projeto', tipo: 'textarea', placeholder: 'Quem vai usar, ver ou receber isso?' },
      { nome: 'referencias', label: 'Referências ou Exemplos', tipo: 'textarea', placeholder: 'Sites, marcas, estilos que gosta ou não gosta' },
      { nome: 'prazo', label: 'Prazo / Entrega Esperada', tipo: 'text', placeholder: 'Ex: 3 semanas, até 15/07' },
    ],
  },
  {
    id: '08_analise_concorrentes',
    nome: 'Análise de Concorrentes com IA',
    icone: '🔭',
    categoria: 'Marca',
    descricao: 'IA compara posicionamento, diferenciais e pontos fracos',
    campos: [
      { nome: 'sua_empresa', label: 'Sua Empresa', tipo: 'text', placeholder: 'Nome da sua empresa' },
      { nome: 'segmento', label: 'Segmento / Mercado', tipo: 'text', placeholder: 'Ex: SaaS de RH, Academia premium' },
      { nome: 'concorrentes', label: 'Concorrentes a Analisar', tipo: 'textarea', placeholder: 'Liste os principais concorrentes' },
      { nome: 'foco', label: 'Foco da Análise', tipo: 'select', opcoes: ['Posicionamento e marca', 'Preços e modelo de negócio', 'Marketing e conteúdo', 'Produto e funcionalidades', 'Análise completa'] },
    ],
  },
  {
    id: '09_faq',
    nome: 'Gerador de FAQ Personalizado',
    icone: '❓',
    categoria: 'Documentos',
    descricao: 'IA cria perguntas frequentes com base nos serviços do cliente',
    campos: [
      { nome: 'empresa', label: 'Empresa / Marca', tipo: 'text', placeholder: 'Nome da empresa' },
      { nome: 'servico', label: 'Serviço ou Produto Principal', tipo: 'textarea', placeholder: 'Descreva o que a empresa oferece' },
      { nome: 'publico', label: 'Público-Alvo', tipo: 'text', placeholder: 'Quem são os clientes típicos' },
      { nome: 'duvidas_comuns', label: 'Dúvidas que Clientes Costumam Ter', tipo: 'textarea', placeholder: 'Liste as dúvidas mais comuns (opcional)' },
    ],
  },
  {
    id: '10_copy_campanhas',
    nome: 'Assistente de Copy para Campanhas',
    icone: '📣',
    categoria: 'Vendas',
    descricao: 'IA gera headline, subhead, CTA e corpo de texto para anúncios',
    campos: [
      { nome: 'produto', label: 'Produto / Serviço', tipo: 'text', placeholder: 'O que está sendo anunciado' },
      { nome: 'publico', label: 'Público-Alvo', tipo: 'text', placeholder: 'Ex: Donos de academia, mães 25-40 anos' },
      { nome: 'beneficio_principal', label: 'Principal Benefício / Transformação', tipo: 'textarea', placeholder: 'O que muda na vida do cliente após usar seu produto' },
      { nome: 'canal', label: 'Canal / Formato', tipo: 'select', opcoes: ['Google Ads', 'Facebook/Instagram Ads', 'LinkedIn Ads', 'Email marketing', 'Landing Page', 'Outdoor/Impresso'] },
      { nome: 'objetivo', label: 'Objetivo da Campanha', tipo: 'select', opcoes: ['Geração de leads', 'Vendas diretas', 'Awareness de marca', 'Retenção / Reengajamento'] },
    ],
  },
  {
    id: '11_calendario_conteudo',
    nome: 'Calendário de Conteúdo Mensal',
    icone: '📅',
    categoria: 'Conteúdo',
    descricao: '30 dias de pautas por pilar estratégico geradas automaticamente',
    campos: [
      { nome: 'nicho', label: 'Nicho / Segmento', tipo: 'text', placeholder: 'Ex: Nutricionista clínica, Coach de carreira' },
      { nome: 'plataforma', label: 'Plataforma Principal', tipo: 'select', opcoes: ['Instagram', 'LinkedIn', 'TikTok', 'YouTube', 'Blog', 'Multi-plataforma'] },
      { nome: 'pilares', label: 'Pilares de Conteúdo', tipo: 'textarea', placeholder: 'Ex: Educação, Bastidores, Depoimentos, Vendas, Motivação' },
      { nome: 'objetivo_mes', label: 'Objetivo do Mês', tipo: 'text', placeholder: 'Ex: Lançar curso, aumentar seguidores, gerar leads' },
      { nome: 'frequencia', label: 'Frequência de Publicação', tipo: 'select', opcoes: ['Diário', '5x por semana', '3x por semana', 'Dias úteis'] },
    ],
  },
  {
    id: '12_icp',
    nome: 'Ferramenta de ICP com IA',
    icone: '🎯',
    categoria: 'Marca',
    descricao: 'IA define cliente ideal com base em dados do negócio',
    campos: [
      { nome: 'produto', label: 'Produto / Serviço Oferecido', tipo: 'textarea', placeholder: 'O que você vende e como funciona' },
      { nome: 'mercado', label: 'Mercado / Setor', tipo: 'text', placeholder: 'Ex: B2B SaaS, Varejo físico, Serviços profissionais' },
      { nome: 'problema_que_resolve', label: 'Problema que Você Resolve', tipo: 'textarea', placeholder: 'Qual dor ou problema o seu produto soluciona' },
      { nome: 'ticket_medio', label: 'Ticket Médio / Faixa de Preço', tipo: 'text', placeholder: 'Ex: R$ 500/mês, R$ 2.000 a R$ 10.000' },
      { nome: 'melhores_clientes', label: 'Características dos Seus Melhores Clientes', tipo: 'textarea', placeholder: 'Se já tem clientes, o que eles têm em comum?' },
    ],
  },
  {
    id: '13_chatbot_clinica',
    nome: 'Chatbot de Triagem para Clínicas',
    icone: '🏥',
    categoria: 'Atendimento',
    descricao: 'Assistente que coleta sintomas, histórico e agenda consulta',
    campos: [
      { nome: 'clinica', label: 'Nome da Clínica', tipo: 'text', placeholder: 'Ex: Clínica São Lucas' },
      { nome: 'especialidade', label: 'Especialidade(s) Médica(s)', tipo: 'text', placeholder: 'Ex: Clínica geral, Dermatologia, Ortopedia' },
      { nome: 'servicos', label: 'Serviços Oferecidos', tipo: 'textarea', placeholder: 'Liste os procedimentos e serviços disponíveis' },
      { nome: 'horarios', label: 'Horários de Atendimento', tipo: 'text', placeholder: 'Ex: Seg-Sex 8h-18h, Sáb 8h-12h' },
    ],
  },
  {
    id: '14_descricao_produto',
    nome: 'Gerador de Descrições de Produto',
    icone: '🛍️',
    categoria: 'Vendas',
    descricao: 'IA escreve descrições persuasivas para e-commerce ou catálogo',
    campos: [
      { nome: 'produto', label: 'Nome do Produto', tipo: 'text', placeholder: 'Nome exato do produto' },
      { nome: 'categoria', label: 'Categoria do Produto', tipo: 'text', placeholder: 'Ex: Suplemento, Roupa fitness, Eletrônico' },
      { nome: 'beneficios', label: 'Principais Benefícios / Características', tipo: 'textarea', placeholder: 'O que este produto faz, diferenciais e specs técnicos' },
      { nome: 'publico', label: 'Público-Alvo', tipo: 'text', placeholder: 'Para quem é este produto' },
      { nome: 'tom', label: 'Tom de Comunicação', tipo: 'select', opcoes: ['Técnico e informativo', 'Emocional e aspiracional', 'Descontraído e jovem', 'Premium e sofisticado', 'Natural e acessível'] },
    ],
  },
  {
    id: '15_newsletter',
    nome: 'Assistente de Criação de Newsletter',
    icone: '📧',
    categoria: 'Conteúdo',
    descricao: 'IA monta newsletter completa com base em tema e audiência',
    campos: [
      { nome: 'tema', label: 'Tema Principal desta Edição', tipo: 'textarea', placeholder: 'Sobre o que será esta newsletter' },
      { nome: 'audiencia', label: 'Audiência / Perfil dos Assinantes', tipo: 'text', placeholder: 'Ex: Empreendedores digitais, Profissionais de RH' },
      { nome: 'tom', label: 'Tom de Voz', tipo: 'select', opcoes: ['Formal e profissional', 'Casual e próximo', 'Educativo e informativo', 'Inspirador', 'Direto e prático'] },
      { nome: 'secoes', label: 'Seções Desejadas', tipo: 'text', placeholder: 'Ex: Abertura, Artigo principal, Dica rápida, Encerramento' },
    ],
  },
  {
    id: '16_revisao_texto',
    nome: 'Revisão e Reescrita de Textos',
    icone: '✏️',
    categoria: 'Documentos',
    descricao: 'IA corrige, adapta tom e otimiza textos do cliente',
    campos: [
      { nome: 'texto', label: 'Texto Original', tipo: 'textarea', placeholder: 'Cole aqui o texto que deseja revisar ou reescrever' },
      { nome: 'objetivo', label: 'Objetivo do Texto', tipo: 'text', placeholder: 'Ex: Post de blog, proposta, email, post de Instagram' },
      { nome: 'tom_desejado', label: 'Tom de Voz Desejado', tipo: 'select', opcoes: ['Formal e profissional', 'Casual e descontraído', 'Persuasivo e vendas', 'Técnico e preciso', 'Acolhedor e empático', 'Inspirador'] },
      { nome: 'ajustes', label: 'Ajustes Específicos Desejados', tipo: 'textarea', placeholder: 'Ex: Deixar mais curto, melhorar o gancho, adicionar CTA' },
    ],
  },
  {
    id: '17_pitch_deck',
    nome: 'Gerador de Pitch Deck com IA',
    icone: '🚀',
    categoria: 'Vendas',
    descricao: 'IA estrutura apresentação comercial com base em dados do negócio',
    campos: [
      { nome: 'empresa', label: 'Nome da Empresa / Startup', tipo: 'text', placeholder: 'Nome da empresa' },
      { nome: 'problema', label: 'Problema que Resolve', tipo: 'textarea', placeholder: 'Qual problema do mercado você resolve' },
      { nome: 'solucao', label: 'Sua Solução', tipo: 'textarea', placeholder: 'Como você resolve esse problema' },
      { nome: 'mercado', label: 'Tamanho do Mercado', tipo: 'text', placeholder: 'Ex: Mercado de R$ 5bi, nossa fatia inicial de R$ 50mi' },
      { nome: 'modelo_negocio', label: 'Modelo de Negócio / Como Monetiza', tipo: 'text', placeholder: 'Ex: SaaS R$ 299/mês, comissão 10%, venda direta' },
      { nome: 'objetivo_pitch', label: 'Objetivo do Pitch', tipo: 'select', opcoes: ['Captação de investimento', 'Parceria comercial', 'Cliente enterprise', 'Aceleração/Incubação'] },
    ],
  },
  {
    id: '18_seo',
    nome: 'Assistente de SEO com IA',
    icone: '🔎',
    categoria: 'Conteúdo',
    descricao: 'IA sugere palavras-chave, títulos e meta descriptions otimizados',
    campos: [
      { nome: 'pagina', label: 'Tema ou URL da Página', tipo: 'text', placeholder: 'Ex: Página sobre consultoria financeira, /blog/investimentos' },
      { nome: 'palavra_chave', label: 'Palavra-Chave Principal', tipo: 'text', placeholder: 'Ex: consultoria financeira para MEI' },
      { nome: 'publico', label: 'Público que Você Quer Atrair', tipo: 'text', placeholder: 'Ex: MEIs buscando declaração de IR' },
      { nome: 'concorrentes_seo', label: 'Concorrentes no Google', tipo: 'text', placeholder: 'Sites concorrentes nas buscas (opcional)' },
    ],
  },
  {
    id: '19_email_personalizado',
    nome: 'Personalização de E-mail com IA',
    icone: '💌',
    categoria: 'Vendas',
    descricao: 'IA adapta corpo do e-mail para cada segmento da base',
    campos: [
      { nome: 'produto', label: 'Produto / Serviço sendo Promovido', tipo: 'text', placeholder: 'O que está sendo oferecido no email' },
      { nome: 'segmentos', label: 'Segmentos da Base', tipo: 'textarea', placeholder: 'Ex: Leads novos, Clientes ativos, Inativos há 90 dias' },
      { nome: 'objetivo', label: 'Objetivo do Email', tipo: 'select', opcoes: ['Venda direta', 'Reengajamento', 'Nutrição de lead', 'Boas-vindas', 'Upsell/Cross-sell', 'Recuperação de carrinho'] },
      { nome: 'tom', label: 'Tom de Voz', tipo: 'select', opcoes: ['Formal', 'Amigável', 'Urgente', 'Exclusivo/Premium', 'Casual'] },
    ],
  },
  {
    id: '20_contrato',
    nome: 'Gerador de Contratos Simples',
    icone: '📜',
    categoria: 'Documentos',
    descricao: 'IA monta contrato de prestação de serviço com base em inputs',
    campos: [
      { nome: 'tipo_servico', label: 'Tipo de Serviço', tipo: 'text', placeholder: 'Ex: Desenvolvimento de site, Consultoria de marketing' },
      { nome: 'contratante', label: 'Contratante (Quem Paga)', tipo: 'text', placeholder: 'Nome / empresa do contratante' },
      { nome: 'contratado', label: 'Contratado (Quem Executa)', tipo: 'text', placeholder: 'Nome / empresa do prestador' },
      { nome: 'valor', label: 'Valor e Forma de Pagamento', tipo: 'text', placeholder: 'Ex: R$ 5.000 em 2x — 50% início, 50% entrega' },
      { nome: 'prazo', label: 'Prazo de Execução', tipo: 'text', placeholder: 'Ex: 30 dias corridos após aprovação do briefing' },
      { nome: 'escopo', label: 'Escopo / O Que Está Incluso', tipo: 'textarea', placeholder: 'Descreva o que será entregue' },
    ],
  },
  {
    id: '21_analise_documento',
    nome: 'Análise de Documentos com IA',
    icone: '📄',
    categoria: 'Documentos',
    descricao: 'IA resume, extrai pontos-chave e interpreta PDFs e contratos',
    campos: [
      { nome: 'texto_documento', label: 'Texto do Documento', tipo: 'textarea', placeholder: 'Cole aqui o texto do documento para análise' },
      { nome: 'tipo_documento', label: 'Tipo de Documento', tipo: 'select', opcoes: ['Contrato', 'Relatório financeiro', 'Proposta comercial', 'Documento jurídico', 'Artigo / Pesquisa', 'E-mail / Comunicado', 'Outro'] },
      { nome: 'foco_analise', label: 'Foco da Análise', tipo: 'select', opcoes: ['Resumo executivo', 'Riscos e cláusulas críticas', 'Pontos de atenção', 'Extração de dados-chave', 'Análise completa'] },
    ],
  },
  {
    id: '22_feedback_alunos',
    nome: 'Feedback Automatizado para Alunos',
    icone: '🎓',
    categoria: 'Educação',
    descricao: 'IA analisa trabalho e devolve feedback estruturado e personalizado',
    campos: [
      { nome: 'disciplina', label: 'Disciplina / Área', tipo: 'text', placeholder: 'Ex: Redação, Cálculo, Marketing Digital, Programação' },
      { nome: 'nivel', label: 'Nível do Aluno', tipo: 'select', opcoes: ['Fundamental', 'Médio', 'Superior', 'Pós-graduação', 'Profissional / Curso livre'] },
      { nome: 'trabalho_aluno', label: 'Trabalho / Resposta do Aluno', tipo: 'textarea', placeholder: 'Cole aqui o trabalho, redação ou resposta do aluno' },
      { nome: 'criterios', label: 'Critérios de Avaliação', tipo: 'textarea', placeholder: 'Ex: Clareza, Argumentação, Gramática, Originalidade (0-10 cada)' },
      { nome: 'tom_feedback', label: 'Tom do Feedback', tipo: 'select', opcoes: ['Encorajador e construtivo', 'Técnico e objetivo', 'Desafiador e rigoroso', 'Gentil e motivador'] },
    ],
  },
  {
    id: '23_script_vendas',
    nome: 'Gerador de Scripts de Vendas',
    icone: '💼',
    categoria: 'Vendas',
    descricao: 'IA cria roteiro de abordagem por etapa do funil e persona',
    campos: [
      { nome: 'produto', label: 'Produto / Serviço', tipo: 'text', placeholder: 'O que está sendo vendido' },
      { nome: 'persona', label: 'Persona / Perfil do Comprador', tipo: 'text', placeholder: 'Ex: Dono de academia de pequeno porte, Gerente de RH' },
      { nome: 'etapa_funil', label: 'Etapa do Funil', tipo: 'select', opcoes: ['Prospecção (primeiro contato)', 'Qualificação', 'Apresentação / Demo', 'Proposta e negociação', 'Follow-up pós-reunião', 'Fechamento', 'Reativação de lead frio'] },
      { nome: 'canal', label: 'Canal de Venda', tipo: 'select', opcoes: ['WhatsApp', 'Email', 'Ligação telefônica', 'Reunião presencial', 'Videochamada', 'LinkedIn'] },
      { nome: 'objecoes', label: 'Principais Objeções que Enfrenta', tipo: 'textarea', placeholder: 'Ex: Muito caro, preciso pensar, já tenho fornecedor' },
    ],
  },
  {
    id: '24_atendimento_ecommerce',
    nome: 'Atendimento para E-commerce',
    icone: '🛒',
    categoria: 'Atendimento',
    descricao: 'IA responde sobre pedidos, prazo, troca e dúvidas de produto',
    campos: [
      { nome: 'loja', label: 'Nome da Loja', tipo: 'text', placeholder: 'Nome do e-commerce' },
      { nome: 'produtos', label: 'Categorias de Produtos', tipo: 'text', placeholder: 'Ex: Moda feminina, Eletrônicos, Suplementos' },
      { nome: 'prazo_entrega', label: 'Prazo Médio de Entrega', tipo: 'text', placeholder: 'Ex: 5-10 dias úteis' },
      { nome: 'politica_devolucao', label: 'Política de Devolução/Troca', tipo: 'textarea', placeholder: 'Descreva as regras de troca, devolução e prazo' },
      { nome: 'canais_suporte', label: 'Canais de Suporte Disponíveis', tipo: 'text', placeholder: 'Ex: WhatsApp, email, chat no site' },
    ],
  },
  {
    id: '25_painel_conteudo',
    nome: 'Painel de Gestão de Conteúdo IA',
    icone: '🎛️',
    categoria: 'Gestão',
    descricao: 'Hub estratégico: planejamento e organização de todo o conteúdo da equipe',
    campos: [
      { nome: 'empresa', label: 'Empresa / Marca', tipo: 'text', placeholder: 'Nome da empresa' },
      { nome: 'equipe', label: 'Tamanho e Perfil da Equipe', tipo: 'text', placeholder: 'Ex: 2 redatores + 1 designer, freelancers' },
      { nome: 'canais_ativos', label: 'Canais de Conteúdo Ativos', tipo: 'text', placeholder: 'Ex: Instagram, Blog, Newsletter, YouTube' },
      { nome: 'objetivos_mensais', label: 'Objetivos e Metas do Mês', tipo: 'textarea', placeholder: 'Ex: Publicar 30 posts, lançar campanha X, atingir Y seguidores' },
      { nome: 'desafios', label: 'Principais Desafios da Equipe', tipo: 'textarea', placeholder: 'Ex: Falta de pauta, conteúdo repetitivo, baixo engajamento' },
    ],
  },
]

export const CATEGORIAS = [...new Set(TEMPLATES.map(t => t.categoria))]

export function getTemplate(id: string): Template | undefined {
  return TEMPLATES.find(t => t.id === id)
}

export function getTemplatesByCategoria(categoria: string): Template[] {
  return TEMPLATES.filter(t => t.categoria === categoria)
}
