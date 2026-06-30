import { FerramentaForm } from './FerramentaForm'

export function generateStaticParams() {
  return [
    { id: '01_roteiro_video' },
    { id: '02_chatbot_atendimento' },
    { id: '03_legendas_redes' },
    { id: '04_proposta_comercial' },
    { id: '05_diagnostico_marca' },
    { id: '06_nomes_marca' },
    { id: '07_briefing' },
    { id: '08_analise_concorrentes' },
    { id: '09_faq' },
    { id: '10_copy_campanhas' },
    { id: '11_calendario_conteudo' },
    { id: '12_icp' },
    { id: '13_chatbot_clinica' },
    { id: '14_descricao_produto' },
    { id: '15_newsletter' },
    { id: '16_revisao_texto' },
    { id: '17_pitch_deck' },
    { id: '18_seo' },
    { id: '19_email_personalizado' },
    { id: '20_contrato' },
    { id: '21_analise_documento' },
    { id: '22_feedback_alunos' },
    { id: '23_script_vendas' },
    { id: '24_atendimento_ecommerce' },
    { id: '25_painel_conteudo' },
  ]
}

export default function Page({ params }: { params: { id: string } }) {
  return <FerramentaForm id={params.id} />
}
