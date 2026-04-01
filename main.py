import streamlit as st

import pandas as pd

from openai import OpenAI

import time

import requests

from requests.auth import HTTPBasicAuth

import json

import re

import concurrent.futures

import urllib.parse

from tenacity import retry, stop_after_attempt, wait_exponential

from pydantic import BaseModel, Field, ValidationError, field_validator



# ==========================================

# 1. CONFIGURAÇÃO DA PÁGINA

# ==========================================

st.set_page_config(page_title="Arco Martech | Motor GEO", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")



# Lógica de Navegação via Query Parameters (Mais estável que botões)

query_params = st.query_params

if 'current_page' not in st.session_state:

    st.session_state['current_page'] = query_params.get("page", "Gerador de Artigos")

if 'show_inputs' not in st.session_state:

    st.session_state['show_inputs'] = False



# ==========================================

# ESTILOS GLOBAIS

# ==========================================

st.markdown("""

    <style>

    /* Importando as fontes do site da Arco */

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Montserrat:wght@400;600;700;800&display=swap');



    /* Forçando a tipografia global */

    html, body, [class*="css"] {

        font-family: 'Inter', sans-serif;

    }



    h1, h2, h3 {

        font-family: 'Montserrat', sans-serif !important;

        font-weight: 700 !important;

        color: #111827 !important;

        letter-spacing: -0.02em;

    }



    /* ESCONDER COMPONENTES NATIVOS DO STREAMLIT */

    [data-testid="stSidebar"], header[data-testid="stHeader"] { display: none !important; }

    .block-container { padding-top: 1rem; max-width: 1200px; }



    .arco-tag {

        display: inline-flex;

        align-items: center;

        background-color: #E8F2FA;

        color: #418EDE !important;

        font-family: 'Montserrat', sans-serif;

        font-weight: 700;

        font-size: 0.75rem;

        letter-spacing: 0.05em;

        padding: 6px 16px;

        border-radius: 50px;

        text-transform: uppercase;

        margin-bottom: 1rem;

    }



    /* === 1. MENU PRINCIPAL COM LOGO ALINHADA === */

    /* Target estrito ao PRIMEIRO grupo de abas da página (O Menu). As sub-abas ignoram isso. */

    div[data-testid="stTabs"]:first-of-type > div > div[data-baseweb="tab-list"] {

        gap: 24px;

        border-bottom: 2px solid #E5E7EB;

        padding-left: 170px; /* Cria o espaço exato para a Logo */

        position: relative;

    }

    /* Injeta a Logo da Arco diretamente dentro da barra de abas principal */

    div[data-testid="stTabs"]:first-of-type > div > div[data-baseweb="tab-list"]::before {

        content: "";

        background-image: url('https://cdn.prod.website-files.com/6810e8cd1c64e82623876ba8/681134835142ef28e05b06ba_logo-arco-dark.svg');

        background-size: contain;

        background-repeat: no-repeat;

        background-position: left center;

        position: absolute;

        left: 0;

        top: 50%;

        transform: translateY(-50%);

        width: 140px;

        height: 35px;

    }

    div[data-testid="stTabs"]:first-of-type > div > div[data-baseweb="tab"] {

        font-family: 'Montserrat', sans-serif;

        font-weight: 600;

        color: #6B7280;

        padding-top: 16px;

        padding-bottom: 16px;

        background: transparent !important;

        border: none !important;

        box-shadow: none !important;

    }

    div[data-testid="stTabs"]:first-of-type > div > div[data-baseweb="tab"][aria-selected="true"] {

        color: #111827 !important;

        border-bottom: 3px solid #F05D23 !important; /* Laranja Arco */

        background: transparent !important;

    }



    /* === 2. TODOS OS BOTÕES PRIMÁRIOS (Quadrados normais 8px) === */

    div[data-testid="stButton"] > button[kind="primary"] {

        background-color: #111827 !important;

        color: #FFFFFF !important;

        border-radius: 8px !important; /* Retorna para o quadrado com canto leve */

        border: none !important;

        padding: 10px 24px !important;

        font-family: 'Inter', sans-serif;

        font-weight: 600 !important;

        height: 3.2em;

        transition: all 0.2s ease-in-out !important;

        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);

    }

    div[data-testid="stButton"] > button[kind="primary"]:hover {

        background-color: #374151 !important;

        transform: translateY(-2px) !important;

    }

    div[data-testid="stButton"] > button[kind="primary"] *,

    div[data-testid="stButton"] > button[kind="primary"] p {

        color: #FFFFFF !important;

        fill: #FFFFFF !important;

        -webkit-text-stroke: 0px transparent !important;

        text-shadow: none !important;

    }



    /* === 3. BOTÃO HERÓI CIRCULAR DA HOME (Exclusivo) === */

    div[data-testid="stElementContainer"]:has(.hero-btn-hook) + div[data-testid="stElementContainer"] div[data-testid="stButton"] > button[kind="primary"] {

        border-radius: 50px !important; /* APENAS se tiver essa classe invisível ele fica redondo */

        height: 54px !important;

    }



    /* ESTILO DOS CARDS DE VENDA */

    .saas-card {

        background: #FFFFFF;

        border: 1px solid #E5E7EB;

        border-radius: 16px;

        padding: 24px;

        height: 100%;

        transition: transform 0.2s, box-shadow 0.2s;

    }

    .saas-card:hover {

        transform: translateY(-5px);

        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);

        border-color: #D1D5DB;

    }

    .card-title {

        font-family: 'Montserrat', sans-serif;

        font-weight: 700;

        font-size: 1.1rem;

        color: #111827;

        margin-bottom: 8px;

    }

    .card-text {

        font-size: 0.9rem;

        color: #4B5563;

        line-height: 1.5;

    }



    /* PIPELINE STYLING */

    .pipeline-container {

        font-family: 'Inter', sans-serif;

        font-size: 0.85em; 

        color: #6B7280; 

        text-align: center;

        margin: 2rem auto;

        background-color: #F9FAFB;

        padding: 12px;

        border-radius: 50px;

        border: 1px solid #E5E7EB;

        width: fit-content;

    }

    .pipeline-step {

        cursor: help; 

        color: #374151;

        font-weight: 500;

        transition: color 0.2s;

    }

    .pipeline-step:hover { color: #F05D23; }



    /* BOTÃO FLUTUANTE DE AJUDA (DIREITA) */

    .floating-help-container {

        position: fixed;

        bottom: 40px;

        right: 40px;

        z-index: 99999;

    }

    div[data-testid="stPopover"] > button {

        background-color: #418EDE !important;

        color: white !important;

        border-radius: 50% !important;

        width: 65px !important;

        height: 65px !important;

        border: none !important;

        box-shadow: 0 10px 15px -3px rgba(226, 27, 34, 0.4) !important;

        display: flex;

        justify-content: center;

        align-items: center;

        transition: transform 0.2s;

        padding: 0 !important;

        margin: 0 !important;

    }

    div[data-testid="stPopover"] > button:hover {

        transform: scale(1.1);

        background-color: #C0141A !important;

    }

    div[data-testid="stPopover"] > button p {

        font-size: 28px !important;

        font-weight: bold;

        margin: 0 !important;

        color: white !important;

    }

    /* Remove as bordas e fundos dos botões do menu */

    div[data-testid="stButton"] > button[kind="secondary"] {

        border: none !important;

        background: transparent !important;

        box-shadow: none !important;

    }

    </style>

""", unsafe_allow_html=True)



# ==========================================

# 1.1 MENU DE NAVEGAÇÃO SAAS NO TOPO

# ==========================================

nav_cols = st.columns([2, 2, 2, 2, 2, 2])



with nav_cols[0]:

    st.markdown('<img src="https://cdn.prod.website-files.com/6810e8cd1c64e82623876ba8/681134835142ef28e05b06ba_logo-arco-dark.svg" style="width: 140px; margin-top: -20px;" alt="Logo Arco">', unsafe_allow_html=True)



opcoes_menu = ["Gerador de Artigos", "BrandBook", "Monitor de GEO", "Revisor de GEO", "Auditor de Artigos"]



# Aplicamos o estilo do menu selecionado DE UMA VEZ AQUI EM CIMA, para não empurrar os botões no loop

try:

    index_selecionado = opcoes_menu.index(st.session_state['current_page'])

    # Usa stroke pra bold sem mudar a largura, e border-bottom na cor laranja

    st.markdown(f"""

    <style>

    div[data-testid="stHorizontalBlock"]:first-of-type div[data-testid="stColumn"]:nth-child({index_selecionado + 2}) button {{

        color: #111827 !important; 

        -webkit-text-stroke: 0.6px #111827 !important;

        border-bottom-color: #F05D23 !important;

    }}

    </style>

    """, unsafe_allow_html=True)

except ValueError:

    pass



# Agora o loop só renderiza os botões, sem injetar tags extras no meio do caminho

for i, opcao in enumerate(opcoes_menu):

    with nav_cols[i+1]:

        if st.button(opcao, use_container_width=True, key=f"nav_{i}"):

            st.session_state['current_page'] = opcao

            st.rerun()



st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)



# ==========================================

# BOTÃO FLUTUANTE DE AJUDA (ESQUERDA)

# ==========================================

st.markdown('<div class="floating-help-container">', unsafe_allow_html=True)

with st.popover("?"):

    st.header("📖 Guia Prático do Motor")

    st.markdown("Bem-vindo à v7.0. Este motor funciona como sua **equipe particular de especialistas**. Ele espiona a concorrência, entende as regras do Google e das IAs, e escreve conteúdos usando a voz exata da sua marca.")

    

    with st.expander("🚀 Como usar as 5 Abas?"):

        st.markdown("""

        **1. Gerador:** Cria artigos completos do zero. Você dá o tema (e links de referência se quiser), ele pesquisa o mercado e redige.

        

        **2. Brandbook:** O 'cérebro' do sistema. É aqui que dizemos o que cada marca da Arco pode ou não falar.

        

        **3. Monitor:** Ferramenta de auditoria. Cole um texto qualquer aqui para a IA dar uma nota de confiabilidade e sugerir melhorias.

        

        **4. Adaptador & Revisor:** Transforme seus E-books/PDFs em artigos "Teaser" para captar Leads, ou conserte textos antigos do blog para voltarem a ranquear.

        

        **5. Auditor de Visibilidade:** Coloque o link de um artigo seu e descubra se o Google ou as IAs já estão recomendando ele.

        """)

        

    with st.expander("📚 O que significam as Notas Matemáticas?"):

        st.markdown("""

        O nosso motor avalia seu texto em duas frentes: **Estrutura** e **Autoridade**.

        

        **Notas de Estrutura:**

        * **Chunk Citability (Legibilidade):** Mede se o texto é fácil de ler. Parágrafos curtos, listas e frases de impacto aumentam a nota.

        * **Answer-First:** Avalia se você enrolou ou se entregou a resposta principal logo no começo do texto.

        

        **Notas de Autoridade:**

        * **Evidence Density (Evidências):** Mede se você usou números, estatísticas reais e links para provar o que diz.

        * **Information Gain (Ineditismo):** Calcula o quanto de informação nova você trouxe em relação ao que já existe no Top 3 do Google.

        * **Entity Coverage:** Avalia se você usou o vocabulário que todo especialista do seu nicho deveria usar.

        """)

        

    with st.expander("🤖 O que são os Testes de IA?"):

        st.markdown("""

        Nós simulamos como o ChatGPT ou Perplexity julgariam o seu texto:

        

        * **Retrieval Simulation:** É a chance de uma IA escolher o seu texto como fonte oficial para responder a um usuário.

        * **Risco de Hijacking:** Mede o risco de um concorrente "roubar" o seu clique por ter explicado o assunto de forma mais direta e didática que você.

        """)

st.markdown('</div>', unsafe_allow_html=True)



# Armazenando o HTML do pipeline para usar depois

pipeline_html = """

<div class="pipeline-container">

    <strong style="color: #111827; font-family: 'Montserrat', sans-serif;">O Caminho do Conteúdo:</strong> 

    <span title="1. Pesquisa: Espiona o Top 3 do Google e as IAs (como ChatGPT) já dizem sobre o tema." class="pipeline-step">1. Pesquisa</span> ➔ 

    <span title="2. Intenção: Descobre a verdadeira dúvida por trás das buscas (o que o leitor quer saber)." class="pipeline-step">2. Intenção</span> ➔ 

    <span title="3. Vocabulário: Mapeia os jargões e conceitos obrigatórios de autoridade." class="pipeline-step">3. Vocabulário</span> ➔ 

    <span title="4. Escrita: Redige o texto usando o tom de voz e regras anti-IA." class="pipeline-step">4. Escrita</span> ➔ 

    <span title="5. Código SEO: Cria os dados ocultos (Schema) para o Google." class="pipeline-step">5. Código SEO</span> ➔ 

    <span title="6. Auditoria: Calcula notas de leitura, resposta direta e evidências." class="pipeline-step">6. Auditoria</span> ➔ 

    <span title="7. Teste de IAs: Simula se o seu texto está bom para virar fonte do SGE." class="pipeline-step">7. Teste de IAs</span>

</div>

"""



# ==========================================

# ESTRUTURAS PYDANTIC

# ==========================================

class MetadadosArtigo(BaseModel):

    title: str = Field(..., description="Título H1 otimizado (max 60 chars)")

    meta_description: str = Field(..., description="Meta description persuasiva (max 150 chars)")

    dicas_imagens: list[str] = Field(..., description="Lista com 2 prompts curtos EM INGLÊS para buscar imagens (ex: ['futuristic classroom', 'student studying'])")

    schema_faq: dict = Field(..., description="Objeto JSON-LD FAQPage completo e idêntico ao texto")



    @field_validator('title', mode='before')

    @classmethod

    def ajustar_tamanho_titulo(cls, v: str) -> str:

        return v



    @field_validator('meta_description', mode='before')

    @classmethod

    def ajustar_tamanho_meta(cls, v: str) -> str:

        return v[:147] + "..." if len(v) > 150 else v



# ==========================================

# 2. BRANDBOOK EMBUTIDO 

# ==========================================

if 'brandbook_df' not in st.session_state:

    dados_iniciais = [

        {

            "Marca": "SAS Educação",

            "URL": "https://www.saseducacao.com.br/",

            "Posicionamento": "Marca visionária, líder em aprovação. Entrega de valor em tecnologia e serviço. | Protagonistas na evolução da forma de ensinar e aprender. Abordagem com diagnósticos e embasamentos profundos, superamos as expectativas de parceiros. Somos alta performance e transformamos complexidade em oportunidades. | Promessa: Educação de excelência com foco em resultados acadêmicos, suporte pedagógico próximo e uso de dados para aprendizado.",

            "Territorios": "Vestibulares, Tecnologia, Inovação, Pesquisas",

            "TomDeVoz": "Acadêmico, inovador, especialista e inspirador. Visionário, colaborativo",

            "PublicoAlvo": "Mantenedores e gestores de escolas médias e grandes, com alto rigor acadêmico e foco em resultados no ENEM. Estudantes, vestibulandos e pais",

            "RegrasNegativas": "Não usar tom professoral antiquado, não prometer aprovação sem esforço.",

            "RegrasPositivas": "Destaque os diferenciais: - Líder nacional em aprovação no SiSU 2025, - Maior sistema de ensino do Brasil, - +1.300 escolas parceiras, - 97% de fidelização. Propósito da marca: Moldar, com coragem e embasamento, a educação do futuro ao lado das escolas."

        },

        {

            "Marca": "Geekie",

            "URL": "https://www.geekie.com.br/",

            "Posicionamento": "Metodologia inovadora (aluno no centro), fácil de implementar. | Material didático inteligente que apoia práticas ativas e que possibilita a personalização da aprendizagem por meio de dados. | Promessa: Aprendizado personalizado, engajante e baseado em dados.",

            "Territorios": "Inovação, IA/Personalização, Tecnologia, Dados",

            "TomDeVoz": "Inovador, moderno, ágil. Transformador, visionário, experimental, adaptável e inspirador",

            "PublicoAlvo": "Mantenedores e Gestores. Diretores de inovação e escolas modernas.",

            "RegrasNegativas": "Não parecer sistema engessado, não usar linguagem punitiva.",

            "RegrasPositivas": "Destaque os diferenciais: - A primeira plataforma de educação baseada em dados, - Mais de 12 milhões de estudantes impactados, - Melhor solução de IA premiada no Top Educação. Propósito da marca: Transformar a educação para que cada estudante seja tratado como único."

        },

        {

            "Marca": "COC",

            "URL": "https://coc.com.br/",

            "Posicionamento": "Marca aprovadora que evolui a escola pedagogicamente. | Promover transformação de alto impacto, através de resultados de crescimento para a gestão da escola e ao longo de toda a trajetória do aluno | Promessa: Resultados de crescimento para a gestão da escola e ao longo de toda a trajetória do aluno.",

            "Territorios": "Vestibulares, Esportes, Gestão escolar, Crescimento",

            "TomDeVoz": "Consultivo, parceiro, dinâmico. Viva, ponta firme, sagaz, aberta, contemporânea",

            "PublicoAlvo": "Mantenedores e Gestores. Coordenadores pedagógicos.",

            "RegrasNegativas": "Não focar discurso apenas no aluno, não usar jargões sem explicação.",

            "RegrasPositivas": "Destaque os diferenciais: - Mais de 60 anos, - Melhor consultoria do Brasil 2x premiada no Top Educação. Propósito: Impulsionar escolas rumo a uma educação contemporânea de excelência."

        },

        {

            "Marca": "Sistema Positivo",

            "URL": "https://www.sistemapositivo.com.br/",

            "Posicionamento": "Formação integral, humana e próxima. A maior rede do Brasil. | Com uma abordagem inspiradora e humana, somos referência em solutions que guiam nossas escolas parceiras a evoluírem na missão de ensinar, transformando positivamente a vida dos brasileiros.",

            "Territorios": "Formação integral, Inclusão, Tradição",

            "TomDeVoz": "Acolhedor, tradicional, humano. Experiente, criativa, inovadora e segura",

            "PublicoAlvo": "Famílias. Mantenedores e Gestores de escolas tradicionais.",

            "RegrasNegativas": "Não parecer frio, não usar jargões técnicos sem contexto acolhedor.",

            "RegrasPositivas": "Destaque os diferenciais: - Mais de 45 anos de atuação. Propósito: Inspirar e fortalecer escolas para que evoluam a educação brasileira com humanidade."

        },

        {

            "Marca": "SAE Digital",

            "URL": "https://sae.digital/",

            "Posicionamento": "Melhor integração físico/digital, hiperatualizada. | Nos consolidamos como o sistema de ensino atualizado, que melhor integra o físico com o digital para potencializar o resultado dos alunos e dos nossos parceiros.",

            "Territorios": "Tecnologia, Inovação Digital",

            "TomDeVoz": "Prático, tecnológico, dinâmico. Jovem, amigável, antenado, parceiro",

            "PublicoAlvo": "Mantenedores e Gestores buscando modernização com custo-benefício.",

            "RegrasNegativas": "Não parecer inacessível, não diminuir a importância do material físico.",

            "RegrasPositivas": "Propósito: Desbravar o caminho para uma educação excelente e acessível, que permita a cada aluno e educador escolher e concretizar seus sonhos."

        },

        {

            "Marca": "Conquista Solução Educacional",

            "URL": "https://www.educacaoconquista.com.br/",

            "Posicionamento": "Solução completa focada na parceria Escola-Família. | Desenvolvimento integral e acessível, a partir de 4 pilares: educação financeira, empreendedorismo, educação socioemocional e família.",

            "Territorios": "Família, Educação Infantil, Valores, Comunidade, Empreendedorismo, Socioemocional",

            "TomDeVoz": "Familiar, parceiro, simples e didático. Integradora, descomplicada",

            "PublicoAlvo": "Pais. Mantenedores e Gestores de escolas de educação infantil.",

            "RegrasNegativas": "Não usar tom corporativo frio, não focar em pressão de vestibular.",

            "RegrasPositivas": "Propósito: Colaborar com escolas para formar alunos protagonistas que constroem seu próprio caminho."

        },

        {

            "Marca": "Escola da Inteligência",

            "URL": "https://escoladainteligencia.com.br/",

            "Posicionamento": "Um ecossistema de educação que transforma alunos, professores, escolas e famílias pelo desenvolvimento da inteligência socioemocional.",

            "Territorios": "Comunidade, Socioemocional, habilidades e competências",

            "TomDeVoz": "Madura, especialista, profunda, humana, acessível, sentimental, suave, estável.",

            "PublicoAlvo": "Mantenedores e Gestores de escolas médias, tradicionais que desejam qualidade e são movidos por um senso de propósito (Ticket alto).",

            "RegrasNegativas": "Evitar linguagem robótica, sem focar excessivamente na competição e em pressões externas.",

            "RegrasPositivas": "Destaque: Primeira solução socioemocional do mercado Brasileiro, presente desde 2010. Tricampeões invictos do Top Educação. Citar ferramentas 'Pulso', 'Mapa Socioemocional' e 'Indicadores Multifocais'. 1.2 milhões de pessoas impactadas."

        },

        {

            "Marca": "PES English",

            "URL": "https://www.pesenglish.com.br/",

            "Posicionamento": "O maior programa de inglês integrado às escolas, facilitador do ensino de qualidade, com resultados que mudam vidas. | Promessa: Educação acessível, integrada e descomplicada.",

            "Territorios": "Bilíngue, crescimento, tecnologia",

            "TomDeVoz": "Especialista, humano, dinâmico, acessível, suave",

            "PublicoAlvo": "Mantenedores e Gestores de escolas que visam escala na educação linguística com custo-benefício para famílias.",

            "RegrasNegativas": "Não prometer fluência irreal em curto prazo, não utilizar termos em inglês soltos sem conexão com o currículo.",

            "RegrasPositivas": "Destaque: 91% de aprovação nos exames de Cambridge, parcerias com Cambridge e Pearson, sistema 'Level Up'. Programa curricular flexível. Mais de 800 escolas, custando 10x menos que curso de idiomas avulso."

        },

        {

            "Marca": "Nave a Vela",

            "URL": "https://www.naveavela.com.br/",

            "Posicionamento": "Referência em educação tecnológica para formar estudantes protagonistas na resolução de problemas reais com tecnologia e criatividade por meio de experiências práticas.",

            "Territorios": "Inovação, tecnologia, criatividade",

            "TomDeVoz": "Especialista, espontâneo, racional, dinâmico",

            "PublicoAlvo": "Mantenedores e Gestore de escolas modernas que valorizam cultura Maker e letramento tecnológico.",

            "RegrasNegativas": "Não desmerecer o ensino tradicional. O foco deve ser a integração complementar.",

            "RegrasPositivas": "Destaque: Abordagem STEAM, 4Cs (criatividade, pensamento crítico, colaboração e comunicação), foco em Inteligência Artificial ética. 4x ganhadores no Top Educação em Educação Tecnológica."

        },

        {

            "Marca": "Programa Pleno",

            "URL": "https://programapleno.com.br/",

            "Posicionamento": "O Pleno transforma o convívio escolar através da educação socioemocional interdisciplinar e com rigor científico, trabalhando saúde mental, física e relações interpessoais.",

            "Territorios": "Projetos, socioemocional, habilidades e competências, bem estar",

            "TomDeVoz": "Coletivo, jovem, dinâmico, espontâneo, sofisticado, humano, especialista",

            "PublicoAlvo": "Mantenedores e Gestores buscando metodologias baseadas em projetos com comprovação científica.",

            "RegrasNegativas": "Não atrelar as soluções como um serviço clínico. É um desenvolvimento escolar de convivência.",

            "RegrasPositivas": "Destaque: Baseado no modelo internacional CASEL, abordagem SAFER, aprendizado baseado em projetos, Guia de trabalho nos espaços públicos e alinhamento à BNCC."

        },

        {

            "Marca": "Gênio das Finanças",

            "URL": "https://geniodasfinancas.com.br/",

            "Posicionamento": "Através da educação financeira comportamental, unimos escolas, alunos e famílias para cultivar autonomia, consciência e equilíbrio nas decisões financeiras, fortalecendo projetos de vida mais saudáveis.",

            "Territorios": "Educação financeira comportamental, habilidades e competências",

            "TomDeVoz": "Dinâmico, specialist, acessível, humano, estável",

            "PublicoAlvo": "Mantenedores e Gestores de escolas focadas em habilidades para a vida do aluno do ensino básico.",

            "RegrasNegativas": "Não usar termos como ficar rico ou fórmulas mágicas. O foco é 'comportamental e equilíbrio', nunca promessas milagrosas.",

            "RegrasPositivas": "Destaque: Educação financeira com propósito, ensinando finanças sem julgamentos e com foco no bem-estar emocional."

        },

        {

            "Marca": "Maralto",

            "URL": "https://maralto.com.br/",

            "Posicionamento": "A Maralto assume a sua responsabilidade no processo de construção de um país leitor e apresenta o Programa de Formação Leitora Maralto com o desejo de promover diálogos em torno do livro, da leitura e dos leitores.",

            "Territorios": "Literatura, associação pedagógica",

            "TomDeVoz": "Coletiva, especialista, sofisticada, humana, profunda, formal",

            "PublicoAlvo": "Educadores que apreciam bibliotecas robustas e incentivo literário profundo.",

            "RegrasNegativas": "Não resumir a literatura a apenas materiais didáticos conteudistas. A chave é 'leitura por prazer e diálogo'.",

            "RegrasPositivas": "Destaque: Investimento autoral em conteúdo literário e visual. Propósito: Formar um país de leitores."

        },

        {

            "Marca": "International School",

            "URL": "https://internationalschool.global/",

            "Posicionamento": "O programa bilíngue mais premiado do Brasil. Pioneira em bilinguismo no país. Prover soluções educacionais consistentes e inovadoras. Transformar vidas por meio da educação bilíngue. Empoderar a comunidade escolar para desenvolver o aluno como ser integral. | Promessa: Resultados concretos no aprendizado.",

            "Territorios": "Bilinguismo, educação, integral, viagens, inovação, pioneirismo",

            "TomDeVoz": "Especialista, inovador, inspirador, prático, pioneiro, parceiro",

            "PublicoAlvo": "Gestores, diretores e coordenadores de escolas. Pais e famílias. Escolas privadas de ticket alto e famílias de classes A, B e C.",

            "RegrasNegativas": "Não usar termos genéricos sem contexto, não soar arrogante ou sabe-tudo. Não inferir que quem aprende inglês é superior ou melhor. Não citar palavras em inglês sem tradução entre parênteses depois. Não focar o discurso somente nos pais (lembrar sempre da figura da escola). NUNCA usar a construção 'neste artigo iremos' ou similares.",

            "RegrasPositivas": "Focar em estrutura informativa. Sempre trazer dados para embasar afirmações vindos de fontes seguras e confiáveis, sempre citar e linkar a fonte dos dados, preferir fontes de pesquisas, governos e instituições de renome. Sempre começar o primeiro parágrafo com um gancho que instigue a leitura, de preferência acompanhado de dado. Podemos usar pesquisas nacionais ou internacionais. Sempre usar construção gramatical focada em clareza: iniciar parágrafos com frases de afirmação, não com conectivos. Sempre conectar com a importância de aprender inglês indo além da gramática: focar na importância de aprender com contexto. Destaque os diferenciais (CSV): Utilização da metodologia CLIL de forma integral. Aborde vivências internacionais reais (KSCIA, Cambridge, Minecraft, Ubisoft, Leo) e a integração do inglês à rotina escolar."

        },

        {

            "Marca": "Isaac",

            "URL": "https://isaac.com.br/",

            "Posicionamento": "A maior plataforma financeira e de gestão para a educação. | Promessa: Mensalidades em dia, sem dor de cabeça.",

            "Territorios": "Gestão financeira, Inovação, dados, tecnologia",

            "TomDeVoz": "Corporativo, direto, analítico. Simples (acessível) e parceiro, especialista em gestão financeira.",

            "PublicoAlvo": "Mantenedores, gestores e diretores financeiros de escolas, faculdades e confessionais.",

            "RegrasNegativas": "Não parecer banco engessado, não usar linguagem infantilizada ou agressiva contra a família devedora.",

            "RegrasPositivas": "Destaque: Diminuição real da inadimplência, 2x premiada no Top educação, excelência técnica, comprometimento e resultados tangíveis."

        },

        {

            "Marca": "ClassApp",

            "URL": "https://www.classapp.com.br/",

            "Posicionamento": "A agenda escolar online melhor avaliada do Brasil | Promessa: Mais que funcionalidades, soluções definitivas para os desafios reais da escola.",

            "Territorios": "Comunicação escolar, gestão, inovação",

            "TomDeVoz": "Autoridade acessível (sabe e explica como faz), empática e humana.",

            "PublicoAlvo": "Mantenedores, gestores, diretores, coordenadores, TI e marketing de escolas.",

            "RegrasNegativas": "Não falar mal do uso do papel de forma grosseira, sempre usar como avanço de modernização.",

            "RegrasPositivas": "Destaque: Adesão de 95% e leitura de 85%, segurança, única vencedora do Top Educação na categoria e mais de 260 mil avaliações com nota 4.8."

        },

        {

            "Marca": "Activesoft",

            "URL": "https://activesoft.com.br/",

            "Posicionamento": "Gestão escolar mais simples e eficiente com a Activesoft: tudo o que sua escola precisa para otimizar processos, ganhar eficiência e alcançar melhores resultados.",

            "Territorios": "Gestão escolar, dados, gestão acadêmica, gestão financeira, administrativa",

            "TomDeVoz": "Simples, acessível, clara e amigável.",

            "PublicoAlvo": "Mantenedores, gestores, diretores e TI de escolas.",

            "RegrasNegativas": "Não usar terminologia muito rebuscada para TI.",

            "RegrasPositivas": "Destaque: Plataforma 100% online (ao contrário de desktops), 25 anos de mercado, atendimento em chat em até 2 minutos (90% de satisfação). Mais de 3 milhões de usuários."

        },

        {

            "Marca": "Arco Educação",

            "URL": "https://www.arcoeducacao.com.br/",

            "Posicionamento": "A plataforma integrada de soluções educacionais da Arco Educação. Ponto de encontro de soluções que simplificam a rotina. +12.000 escolas parceiras e +4 milhões de alunos. | Promessa: Tudo que a educação precisa, em um só lugar.",

            "Territorios": "Conexão e tecnologia, foco no elo entre gestão e família (herança isaac/ClassApp).",

            "TomDeVoz": "Confiável, estratégica: torna o complicado mais simples, conecta o que estava separado.",

            "PublicoAlvo": "Mantenedores, gestores e diretores. Professores. Famílias. Alunos.",

            "RegrasNegativas": "Não apresentar como um simples repositório, mas como um ecossistema.",

            "RegrasPositivas": "Destaque: Apenas uma marca com o tamanho e história da Arco conseguiria reunir o melhor de pedagógico, gestão e tecnologia em um só lugar."

        }

    ]

    st.session_state['brandbook_df'] = pd.DataFrame(dados_iniciais)



# ==========================================

# 2.1 BASE DE DADOS DOS ESPECIALISTAS (GHOSTWRITING)

# ==========================================

if 'especialistas_df' not in st.session_state:

    dados_especialistas = [

        {"Especialista": "Professor Idelfranio Moreira De Sousa", "Link do Artigo": "https://exemplo.com"},

        {"Especialista": "Professor Ademar Celedonio Guimaraes Junior", "Link do Artigo": "https://www.linkedin.com/pulse/alunos-mais-ricos-do-brasil-t%25C3%25AAm-notas-inferiores-aos-celed%25C3%25B4nio-g-jr-eav6f/"},

        {"Especialista": "Professor Ademar Celedonio Guimaraes Junior", "Link do Artigo": "https://www.linkedin.com/pulse/como-atualidades-podem-ser-cobradas-enem-ademar-celed%25C3%25B4nio-g-jr-cjedf/"},

        {"Especialista": "Professor Ademar Celedonio Guimaraes Junior", "Link do Artigo": "https://www.linkedin.com/pulse/como-educa%25C3%25A7%25C3%25A3o-do-futuro-pode-ser-moldada-partir-uso-celed%25C3%25B4nio-g-jr-4cl7f/"},

        {"Especialista": "Professor Ademar Celedonio Guimaraes Junior", "Link do Artigo": "https://www.linkedin.com/pulse/l%25C3%25ADderes-que-moldam-vidas-celebrando-o-dia-do-diretor-celed%25C3%25B4nio-g-jr-iyizf/"},

        {"Especialista": "Professor Ademar Celedonio Guimaraes Junior", "Link do Artigo": "https://www.linkedin.com/pulse/vacinas-de-mrna-da-rejei%25C3%25A7%25C3%25A3o-acad%25C3%25AAmica-ao-pr%25C3%25AAmio-nobel-ademar/"},

        {"Especialista": "Professor Ademar Celedonio Guimaraes Junior", "Link do Artigo": "https://www.linkedin.com/pulse/5-formas-de-investir-na-educa%25C3%25A7%25C3%25A3o-do-seu-filho-e-o-celed%25C3%25B4nio-g-jr/"},

        {"Especialista": "Professor Ademar Celedonio Guimaraes Junior", "Link do Artigo": "https://www.linkedin.com/pulse/construindo-repert%25C3%25B3rio-cultural-para-o-enem-e-fuvest-celed%25C3%25B4nio-g-jr/"},

        {"Especialista": "Professor Ademar Celedonio Guimaraes Junior", "Link do Artigo": "https://www.linkedin.com/pulse/bncc-e-educa%25C3%25A7%25C3%25A3o-midi%25C3%25A1tica-ferramentas-cruciais-em-um-celed%25C3%25B4nio-g-jr/"},

        {"Especialista": "Professor Ademar Celedonio Guimaraes Junior", "Link do Artigo": "https://www.linkedin.com/pulse/quanto-maior-o-investimento-em-tecnologia-ser%25C3%25A1-de-celed%25C3%25B4nio-g-jr/"},

        {"Especialista": "Professor Ademar Celedonio Guimaraes Junior", "Link do Artigo": "https://www.linkedin.com/pulse/censo-escolar-2025-brasil-perde-11-milh%C3%A3o-de-alunos-ademar-m1oae/"}

    ]

    st.session_state['especialistas_df'] = pd.DataFrame(dados_especialistas)

    

# ==========================================

# 3. CONEXÃO SEGURA E CREDENCIAIS

# ==========================================

try:

    TOKEN = st.secrets["OPENROUTER_KEY"]

except Exception:

    TOKEN = None



try:

    SERPAPI_KEY = st.secrets["SERPAPI_KEY"]

except Exception:

    SERPAPI_KEY = None



def obter_credenciais_cms(marca):

    """Busca as credenciais (WP ou Drupal) da marca nos secrets."""

    try:

        if "wordpress" in st.secrets and marca in st.secrets["wordpress"]:

            creds = st.secrets["wordpress"][marca]

            return creds.get("WP_URL", ""), creds.get("WP_USER", ""), creds.get("WP_APP_PASSWORD", ""), creds.get("CMS_TYPE", "wp").lower()

    except Exception:

        pass

    return "", "", "", "wp"

# ==========================================

# 3.2 FUNÇÕES DE CONTEXTO E BUSCA

# ==========================================

@st.cache_data(ttl=3600, show_spinner=False)

def buscar_contexto_google(palavra_chave):

    if not SERPAPI_KEY:

        return "Sem chave Serper configurada. Pule o contexto do Google."

    url = "https://google.serper.dev/search"

    payload = json.dumps({"q": palavra_chave, "gl": "br", "hl": "pt-br"})

    headers = {'X-API-KEY': SERPAPI_KEY, 'Content-Type': 'application/json'}

    try:

        response = requests.request("POST", url, headers=headers, data=payload)

        dados = response.json()

        contexto_extraido = []

        if "answerBox" in dados:

            snippet = dados["answerBox"].get("snippet") or dados["answerBox"].get("answer", "Sem texto")

            contexto_extraido.append(f"📍 GOOGLE FEATURED SNIPPET ATUAL:\n{snippet}\n")

        if "knowledgeGraph" in dados:

            desc = dados["knowledgeGraph"].get("description", "")

            contexto_extraido.append(f"🧠 GOOGLE KNOWLEDGE GRAPH:\n{desc}\n")

        if "organic" in dados:

            contexto_extraido.append("📊 TOP 3 RESULTADOS ORGÂNICOS (CONTEÚDO LIDO VIA JINA):")



            def buscar_jina(res_item, index):

                titulo = res_item.get('title', 'Sem Título')

                snippet = res_item.get('snippet', 'Sem Snippet')

                link = res_item.get('link', '')

                conteudo_real = ""

                if link:

                    try:

                        jina_headers = {

                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',

                            'X-Return-Format': 'markdown',

                            'Accept': 'text/plain'

                        }

                        jina_res = requests.get(f"https://r.jina.ai/{link}", headers=jina_headers, timeout=12)

                        if jina_res.status_code == 200:

                            conteudo_real = jina_res.text[:1500]

                    except Exception:

                        conteudo_real = "Falha ao ler o conteúdo integral."

                return f"{index+1}. Título: {titulo}\n Snippet: {snippet}\n Link: {link}\n Conteúdo:\n{conteudo_real}\n"



            with concurrent.futures.ThreadPoolExecutor() as executor:

                resultados_jina = list(executor.map(lambda x: buscar_jina(x[1], x[0]), enumerate(dados["organic"][:3])))

            contexto_extraido.extend(resultados_jina)

        resultado_final = "\n".join(contexto_extraido)

        return resultado_final if resultado_final else "Sem resultados orgânicos relevantes."

    except Exception as e:

        return f"Erro ao coletar dados do Google (Serper): {e}"



@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))

def chamar_llm(system_prompt, user_prompt, model, temperature=0.3, response_format=None):

    client = OpenAI(

        base_url="https://openrouter.ai/api/v1",

        api_key=TOKEN,

        default_headers={"HTTP-Referer": "https://arcomartech.com", "X-Title": "Gerador GEO WP"}

    )

    kwargs = {

        "model": model,

        "messages": [

            {"role": "system", "content": system_prompt},

            {"role": "user", "content": user_prompt}

        ],

        "temperature": temperature,

    }

    if response_format:

        kwargs["response_format"] = response_format

    response = client.chat.completions.create(**kwargs)

    return response.choices[0].message.content



@st.cache_data(ttl=3600, show_spinner=False)

def buscar_baseline_llm(palavra_chave):

    system_prompt = "Você é um pesquisador de IA sênior. Forneça a resposta que uma IA daria hoje para o termo pesquisado, citando o consenso atual."

    user_prompt = f"O que você sabe sobre: '{palavra_chave}'? Retorne um resumo profundo de como esse tema é respondido atualmente pelas IAs."

    try:

        return chamar_llm(system_prompt, user_prompt, model="openai/gpt-4o-mini", temperature=0.1)

    except Exception as e:

        return f"Erro ao buscar Baseline de IA: {e}"



@st.cache_data(ttl=3600, show_spinner=False)

def buscar_artigos_relacionados_wp(palavra_chave, wp_url, wp_user, wp_pwd):

    """

    RAG Reverso dinâmico: Busca artigos já publicados no WP da marca selecionada para linkagem interna.

    Lida com URLs formatadas com /wp-json/ ou com ?rest_route= contornando CloudFront.

    """

    if not (wp_url and wp_user and wp_pwd):

        return "Sem credenciais do WordPress configuradas para esta marca. Pule a linkagem interna."

    

    import base64

    wp_pwd_clean = wp_pwd.replace(" ", "").strip()

    credenciais = f"{wp_user}:{wp_pwd_clean}"

    token_auth = base64.b64encode(credenciais.encode('utf-8')).decode('utf-8')

    

    # Mesma Máscara Robusta que funcionou no POST

    headers = {

        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',

        'Accept': 'application/json, text/plain, */*',

        'Authorization': f'Basic {token_auth}',

        'Connection': 'keep-alive',

        'Accept-Encoding': 'gzip, deflate, br'

    }



    # Adapta a URL dinamicamente garantindo que não quebre a query

    separador = "&" if "?" in wp_url else "?"

    search_url = f"{wp_url}{separador}search={urllib.parse.quote(palavra_chave)}&per_page=3&_fields=id,title,link"

    

    try:

        response = requests.get(search_url, headers=headers, timeout=15)

        if response.status_code == 200:

            posts = response.json()

            if not posts:

                return "Nenhum artigo interno altamente relacionado encontrado no WordPress desta marca."

            

            contexto_interno = "🔗 ARTIGOS DO PRÓPRIO BLOG (RAG REVERSO):\n"

            for p in posts:

                titulo = p.get("title", {}).get("rendered", "Sem título")

                link = p.get("link", "")

                contexto_interno += f"- Título: {titulo}\n  URL: {link}\n"

            return contexto_interno

        else:

            return f"Erro na busca WP (Status {response.status_code}): O Firewall bloqueou a leitura."

    except Exception as e:

        return f"Falha ao conectar com WP da marca para RAG Reverso: {e}"



@st.cache_data(ttl=3600, show_spinner=False)

def buscar_artigos_relacionados_drupal(palavra_chave, d_url, d_user, d_pwd):

    if not (d_url and d_user and d_pwd): return "Sem credenciais Drupal."

    import base64

    token_auth = base64.b64encode(f"{d_user}:{d_pwd.replace(' ', '').strip()}".encode('utf-8')).decode('utf-8')

    headers = {

        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', 

        'Accept': 'application/vnd.api+json', 

        'Authorization': f'Basic {token_auth}'

    }

    

    filtro = f"?filter[title-filter][condition][path]=title&filter[title-filter][condition][operator]=CONTAINS&filter[title-filter][condition][value]={urllib.parse.quote(palavra_chave)}&page[limit]=3"

    try:

        res = requests.get(f"{d_url}{filtro}", headers=headers, timeout=15)

        if res.status_code == 200:

            posts = res.json().get("data", [])

            if not posts: return "Nenhum artigo encontrado no Drupal."

            ctx = "🔗 ARTIGOS DO PRÓPRIO BLOG (RAG REVERSO DRUPAL):\n"

            for p in posts:

                attrs = p.get("attributes", {})

                titulo = attrs.get('title', '')

                

                # Proteção contra path nulo

                path_data = attrs.get('path') or {}

                link = path_data.get('alias', '') if isinstance(path_data, dict) else ""

                

                ctx += f"- Título: {titulo}\n  URL: {link}\n"

            return ctx

        return f"Erro Drupal RAG (Status {res.status_code})"

    except Exception as e:

        return f"Erro Drupal RAG: {e}"



@st.cache_data(ttl=3600, show_spinner=False)

def buscar_estilo_especialista(nome_especialista, df_especialistas):

    """Puxa até 3 artigos do especialista via Jina AI para a IA clonar o estilo de escrita."""

    if not nome_especialista: return ""

    

    links = df_especialistas[df_especialistas['Especialista'] == nome_especialista]['Link do Artigo'].tolist()

    import random

    links_selecionados = random.sample(links, min(3, len(links))) # Pega 3 aleatórios para não estourar limite

    

    contexto = f"📚 CLONAGEM DE PERSONA E REFERÊNCIAS: {nome_especialista}\n"

    

    for link in links_selecionados:

        try:

            jina_headers = {'User-Agent': 'Mozilla/5.0', 'X-Return-Format': 'markdown', 'Accept': 'text/plain'}

            res = requests.get(f"https://r.jina.ai/{link}", headers=jina_headers, timeout=12)

            if res.status_code == 200:

                contexto += f"\n--- Artigo Anterior Escrito por {nome_especialista} ---\n"

                contexto += res.text[:1500] + "...\n" # Pega os primeiros 1500 chars (o ouro do tom de voz)

        except Exception:

            pass

            

    return contexto



@st.cache_data(ttl=300, show_spinner=False)

def listar_posts_wp(wp_url, wp_user, wp_pwd):

    """

    Busca os últimos posts do WP para a aba de Revisão e Auditoria usando máscara de Chrome.

    """

    if not (wp_url and wp_user and wp_pwd):

        return []

    

    import base64

    wp_pwd_clean = wp_pwd.replace(" ", "").strip()

    credenciais = f"{wp_user}:{wp_pwd_clean}"

    token_auth = base64.b64encode(credenciais.encode('utf-8')).decode('utf-8')

    

    # Adicionada a mesma máscara do Ping para driblar o WAF do COC

    headers = {

        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',

        'Accept': 'application/json',

        'Authorization': f'Basic {token_auth}',

        'Connection': 'keep-alive'

    }



    separador = "&" if "?" in wp_url else "?"

    

    # Removido o 'draft' para evitar erro 401/403 caso a senha de app tenha privilégios reduzidos

    search_url = f"{wp_url}{separador}per_page=15&status=publish&_fields=id,title,content,link"

    

    try:

        # Aumentamos o timeout para 25s, pois puxar 15 posts do COC pode demorar mais que o ping

        res = requests.get(search_url, headers=headers, timeout=25)

        if res.status_code == 200:

            return res.json()

        else:

            print(f"Erro ao listar posts WP: {res.status_code} - {res.text}")

    except Exception as e:

        print(f"Timeout ou erro na requisição WP: {e}")

        pass

        

    return []



@st.cache_data(ttl=300, show_spinner=False)

def listar_posts_drupal(d_url, d_user, d_pwd):

    if not (d_url and d_user and d_pwd): return []

    import base64

    token_auth = base64.b64encode(f"{d_user}:{d_pwd.replace(' ', '').strip()}".encode('utf-8')).decode('utf-8')

    headers = {

        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', 

        'Accept': 'application/vnd.api+json', 

        'Authorization': f'Basic {token_auth}'

    }

    try:

        res = requests.get(f"{d_url}?sort=-created&page[limit]=15", headers=headers, timeout=15)

        if res.status_code == 200:

            posts = res.json().get("data", [])

            

            lista_formatada = []

            for p in posts:

                attrs = p.get("attributes", {})

                titulo = attrs.get("title") or "Sem Título"

                

                # Proteção contra body nulo

                body_data = attrs.get("body") or {}

                conteudo = body_data.get("value", "") if isinstance(body_data, dict) else ""

                

                lista_formatada.append({

                    "id": p.get("id"),

                    "title": {"rendered": titulo},

                    "content": {"rendered": conteudo}

                })

            return lista_formatada

    except Exception as e:

        print(f"Erro no parser do Drupal: {e}")

        pass

    return []

    

# ==========================================================

# NOVAS FUNÇÕES INCREMENTAIS DE ROBUSTEZ E GEO (v5 e v6)

# ==========================================================



def gerar_reverse_queries(palavra_chave):

    system = """

    

    Você é um analista de comportamento de LLMs e SearchGPT.

    Dada uma keyword principal, gere perguntas que mecanismos de IA provavelmente fazem internamente para construir respostas e as perguntas mais comuns e básicas feitas por usuários reais no Google.

    Retorne APENAS um JSON estrito:

    {

     "user_questions": ["pergunta1", "pergunta2", "pergunta3", "pergunta4"],

     "llm_reasoning_questions": ["pergunta1", "pergunta2"],

     "semantic_depth_questions": ["pergunta1", "pergunta2"]

    }

    """

    try:

        return chamar_llm(system, f"Keyword principal: {palavra_chave}", "openai/gpt-4o-mini", 0.1, response_format={"type": "json_object"})

    except Exception as e:

        return "{}"



def analisar_entity_gap(contexto_google, palavra_chave):

    system = """

    Você é um analista de SEO semântico e estrategista de conteúdo.

    Analise o conteúdo do TOP 3 do Google extraído.

    Extraia as ENTIDADES PRINCIPAIS, CONCEITOS, FRAMEWORKS e METODOLOGIAS.

    Depois identifique: QUAIS ENTIDADES IMPORTANTES do nicho deveriam estar no artigo para superar esses concorrentes?

    """

    user = f"Palavra-chave: {palavra_chave}\nConteúdo dos Concorrentes:\n{contexto_google}"

    return chamar_llm(system, user, "openai/gpt-4o-mini", 0.1)



def avaliar_originalidade(artigo_html, contexto_google):

    system = """

    Você é um auditor de plágio semântico e originalidade E-E-A-T.

    Compare o artigo gerado com o TOP 3 do Google.

    Avalie o 'Information Gain' (Ganho de Informação). O artigo trouxe ângulos novos? 

    Retorne uma NOTA DE ORIGINALIDADE de 0 a 100 e uma justificativa curta.

    """

    user = f"ARTIGO GERADO:\n{artigo_html}\n\nTOP GOOGLE:\n{contexto_google}"

    return chamar_llm(system, user, "openai/gpt-4o-mini", 0.1)



def prever_citabilidade_llm(artigo_html, palavra_chave):

    system = """

    Você é o algoritmo de RAG de um buscador baseado em IA (como Perplexity ou Gemini).

    Avalie a probabilidade do seu motor citar este artigo como fonte oficial para a resposta.

    Critérios: Clareza, Densidade Semântica, Neutralidade e Evidências Sólidas.

    Retorne APENAS um JSON:

    {

      "citabilidade_score": "nota de 0 a 100",

      "motivo": "explicação"

    }

    """

    user = f"ARTIGO:\n{artigo_html}\n\nKEYWORD: {palavra_chave}"

    return chamar_llm(system, user, "openai/gpt-4o-mini", 0.1, response_format={"type":"json_object"})



def gerar_cluster(palavra_chave):

    system = """

    Você é um Arquiteto de SEO (Topical Authority).

    Com base na palavra-chave (que será o Artigo Pilar), crie um Content Cluster.

    Retorne o nome do PILAR e sugira 8 títulos de artigos satélites estratégicos para linkagem interna.

    """

    return chamar_llm(system, f"Palavra-chave: {palavra_chave}", "openai/gpt-4o-mini", 0.3)



def calcular_citation_score(artigo_html):

    score = 0

    if "<strong>Definição:" in artigo_html or "<strong>Definição" in artigo_html: score += 1

    if "<strong>Resposta direta:" in artigo_html or "<strong>Resposta direta" in artigo_html: score += 1

    if "Resumo Estratégico" in artigo_html or "Resumo estratégico" in artigo_html: score += 1

    if "Segundo especialistas" in artigo_html or "Especialistas" in artigo_html: score += 1

    if "Perguntas Frequentes" in artigo_html: score += 1

    return f"{score}/5"



def calcular_entity_coverage(artigo_html, entity_gap_text):

    system = """

    Você é um analisador de SEO semântico.

    Compare:

    1) ENTIDADES importantes sugeridas (Entity Gap)

    2) ENTIDADES presentes no artigo

    Retorne um JSON:

    {

      "entity_coverage_score": "0-100",

      "entities_present": [],

      "entities_missing": []

    }

    """

    user = f"ENTIDADES RECOMENDADAS:\n{entity_gap_text}\n\nARTIGO:\n{artigo_html}"

    return chamar_llm(system, user, "openai/gpt-4o-mini", 0.1, response_format={"type":"json_object"})



def simular_llm_retrieval(keyword, artigo_html):

    system = """

    Você simula o processo de recuperação de fontes usado por motores de busca baseados em LLM.

    Dada uma pergunta do usuário e um artigo, avalie se o conteúdo seria selecionado como fonte.

    Considere: clareza, estrutura citável, entidades confiáveis, completude, neutralidade.

    Retorne JSON:

    {

      "retrieval_score": "0-100",

      "chance_de_ser_usado_como_fonte": "baixa | média | alta",

      "motivo": "explicação curta"

    }

    """

    user = f"PERGUNTA DO USUÁRIO:\n{keyword}\n\nARTIGO:\n{artigo_html}"

    return chamar_llm(system, user, "openai/gpt-4o-mini", 0.1, response_format={"type":"json_object"})



def detectar_citation_hijacking(artigo_html):

    system = """

    Analise o artigo e identifique vulnerabilidade a AI Citation Hijacking.

    Citation Hijacking acontece quando outro conteúdo concorrente pode responder melhor ou mais direto à mesma pergunta.

    Avalie: ausência de resposta direta, falta de definição clara, falta de estrutura citável, excesso de narrativa.

    Retorne JSON:

    {

      "risco_hijacking": "baixo | médio | alto",

      "pontos_fracos": [],

      "melhorias_recomendadas": []

    }

    """

    user = f"ARTIGO:\n{artigo_html}"

    return chamar_llm(system, user, "openai/gpt-4o-mini", 0.1, response_format={"type":"json_object"})



def simular_resposta_ai(keyword, artigo_html):

    system = """

    Simule como um motor de busca baseado em IA (SGE/Perplexity) responderia a uma pergunta do usuário usando o artigo fornecido APENAS como fonte.

    Produza a resposta final que o usuário veria.

    Depois avalie: clareza, completude, necessidade de outras fontes.

    Retorne JSON:

    {

      "resposta_simulada": "...",

      "qualidade_resposta": "0-100",

      "precisaria_de_outras_fontes": true | false

    }

    """

    user = f"PERGUNTA:\n{keyword}\n\nFONTE:\n{artigo_html}"

    return chamar_llm(system, user, "openai/gpt-4o-mini", 0.2, response_format={"type":"json_object"})



def executar_revisao_geo_wp(palavra_chave, publico, marca, html_atual):

    df = st.session_state['brandbook_df']

    marca_info = df[df['Marca'] == marca].iloc[0].to_dict()

    url_marca = marca_info.get('URL', '')



    system = """Você é um Revisor Sênior de SEO e Engenheiro de Prompt GEO.

    Sua missão é avaliar um artigo HTML antigo ou mal formatado e reescrevê-lo para atingir a nota máxima nos critérios E-E-A-T e nas heurísticas do Motor GEO.

    

    DIRETRIZES DE REVISÃO E REESCRITA OBRIGATÓRIAS:

    1. ASSIMETRIA VISUAL EXTREMA: Destrua blocos de texto maciços. Intercale parágrafos "maiores" (3-4 linhas) com parágrafos de UMA ÚNICA FRASE (respiro visual profundo). É proibido que os parágrafos tenham tamanho simétrico.

    2. ANSWER-FIRST: Crie um <h2>Resposta rápida para: [palavra-chave]</h2> logo no início e entregue a resposta mastigada em 2 linhas com a tag <p><strong>Resposta direta:</strong>.

    3. CHUNK CITABILITY: Insira um <p><strong>Definição:</strong> com menos de 30 palavras no início. Limite listas (<ul>) a no máximo 2 em todo o artigo.

    4. BRANDBOOK DA MARCA: Reescreva trechos fora de tom usando o Tom de Voz e Posicionamento exigidos no briefing. Garanta que o nome da marca seja linkado para a URL oficial.

    5. PRESERVAÇÃO DE DADOS: Mantenha as informações e ideias do texto original. Não invente "Estudos da OCDE" ou dados matemáticos se eles não estiverem no texto original.

    6. Mantenha os marcadores `<br>Resumo Estratégico<br>` e `<br>Perguntas Frequentes<br>` onde achar pertinente para o novo esqueleto.

    7. PRESERVAÇÃO DE LINKS E IMAGENS (REGRA INTOCÁVEL): É ESTRITAMENTE PROIBIDO remover, alterar URLs, ou deletar tags `<a>` (hiperlinks), `<img>` e `<figure>` que já estão no HTML original. Você deve reposicioná-las logicamente no novo texto, mantendo os atributos `href`, `src` e classes intactos. O seu trabalho é melhorar o copywriting e a estrutura em volta da mídia, NUNCA apagar o trabalho de linkagem interna/externa e imagens que o redator original já fez.

    8. CORREÇÃO DE CAPITALIZAÇÃO (CRÍTICO): Revise todos os títulos (H1, H2, H3). Se eles estiverem em "Title Case" (Todas As Iniciais Maiúsculas), reescreva-os IMEDIATAMENTE para o padrão brasileiro "Sentence Case" (Apenas a primeira letra e nomes próprios em maiúscula).

    

    RETORNE EXCLUSIVAMENTE UM JSON SEGUINDO ESTE FORMATO EXATO:

    {

        "diagnostico": "Resumo curto das falhas originais de SEO/GEO encontradas.",

        "melhorias_aplicadas": ["Melhoria 1", "Melhoria 2"],

        "html_novo": "O código HTML completo reescrito e otimizado"

    }

    """

    

    user = f"""

    PALAVRA-CHAVE FOCO: '{palavra_chave}'

    PÚBLICO-ALVO: {publico}

    MARCA ALVO: {marca}

    URL DA MARCA OBRIGATÓRIA: {url_marca}

    

    DIRETRIZES DA MARCA ({marca}):

    - Posicionamento: {marca_info['Posicionamento']}

    - Tom de Voz Exigido: {marca_info['TomDeVoz']}

    - Regras Positivas: {marca_info.get('RegrasPositivas', '')}

    - Proibido (Regras Negativas): {marca_info['RegrasNegativas']}

    

    TEXTO ORIGINAL PARA AUDITORIA E REESCRITA (HTML):

    {html_atual}

    """

    

    return chamar_llm(system, user, model="anthropic/claude-3.7-sonnet", temperature=0.3, response_format={"type": "json_object"})



# ==========================================================

# NOVAS MÉTRICAS MATEMÁTICAS RAG / GEO (V7.0)

# ==========================================================

def extrair_numero(valor):

    try:

        if isinstance(valor, dict):

            valor = json.dumps(valor)

        match = re.search(r'\d+', str(valor))

        if match:

            return int(match.group())

    except:

        pass

    return 0



def calcular_geo_score_matematico(citation_score, originalidade, citabilidade, entity_coverage_str):

    # Converte tudo para número

    citation = extrair_numero(citation_score) * 20  # Multiplica por 20 para virar escala 0-100

    original = extrair_numero(originalidade)

    cita_llm = extrair_numero(citabilidade)

    

    # Extrai o score de entidades do dict que a IA gerou antes

    try:

        entity_dict = json.loads(entity_coverage_str)

        entity = int(entity_dict.get("entity_coverage_score", 0))

    except:

        entity = extrair_numero(entity_coverage_str)



    # Cálculo Ponderado Matemático (Soma 100%)

    geo = (0.35 * citation) + (0.25 * cita_llm) + (0.25 * entity) + (0.15 * original)



    return {

        "citation_score_normalizado": f"{citation}/100",

        "citabilidade_llm": cita_llm,

        "originalidade": original,

        "entity_coverage": entity,

        "geo_score_final": round(geo, 2),

        "veredito": "Score calculado matematicamente via heurística RAG com pesos fixos (não subjetivo)."

    }



def avaliar_chunk_citability(artigo_html):

    paragrafos = artigo_html.split("</p>")

    definicoes = 0

    listas = artigo_html.count("<li>")

    paragrafos_curtos = 0



    for p in paragrafos:

        texto_limpo = re.sub(r'<[^>]+>', '', p).strip()

        palavras = len(texto_limpo.split())

        if ":" in texto_limpo and palavras < 40 and palavras > 5:

            definicoes += 1

        if 10 < palavras < 35:

            paragrafos_curtos += 1



    # NOVA LÓGICA DE FREIO: Máximo de 15 pontos para listas (aprox. 5 itens no total)

    pontos_lista = min(listas * 3, 15)



    score = (definicoes * 10) + pontos_lista + (paragrafos_curtos * 2)

    score = min(score, 100)

    return {

        "chunk_citability_score": score,

        "definicoes_estrategicas_detectadas": definicoes,

        "itens_de_lista": listas,

        "paragrafos_de_leitura_rapida": paragrafos_curtos

    }



def avaliar_answer_first(artigo_html):

    inicio = artigo_html[:800].lower()

    padroes = ["resposta direta:", "definição:", "é ", "refere-se", "significa"]

    for p in padroes:

        if p in inicio:

            return {"answer_first_score": 100, "padrao_detectado": p, "status": "Excelente (Resposta no Topo)"}

    return {"answer_first_score": 40, "padrao_detectado": "nenhum", "status": "Alerta: A IA pode ter dificuldade de achar a resposta rápida."}



def simular_rag_chunks(artigo_html, keyword):

    chunks = artigo_html.split("\n\n")

    resultados = []

    for c in chunks:

        texto_limpo = re.sub(r'<[^>]+>', '', c).strip()

        if not texto_limpo: continue

        score = 0

        palavras = texto_limpo.lower()

        if keyword.lower() in palavras:

            score += 30

        score += palavras.count(keyword.lower()) * 5

        if ":" in texto_limpo: score += 10

        if len(texto_limpo.split()) < 45: score += 10

        resultados.append({"chunk": texto_limpo[:150] + "...", "score": score})

    

    top_chunks = sorted(resultados, key=lambda x: x["score"], reverse=True)[:3]

    return {"top_chunks_para_llm": top_chunks, "retrieval_strength": round(sum([c["score"] for c in top_chunks])/3, 2) if top_chunks else 0}



def calcular_evidence_density(artigo_html):

    texto_limpo = re.sub(r'<[^>]+>', '', artigo_html).strip()

    numeros = len(re.findall(r'\b\d+\b', texto_limpo))

    porcentagens = len(re.findall(r'\d+%', texto_limpo))

    links = artigo_html.count("href=")

    score = min((numeros * 2) + (porcentagens * 5) + (links * 10), 100)

    return {"evidence_density_score": score, "numeros_absolutos": numeros, "porcentagens": porcentagens, "links_de_referencia": links}



def calcular_information_gain(artigo_html, google_ctx):

    palavras_artigo = set(re.findall(r'\w+', re.sub(r'<[^>]+>', '', artigo_html).lower()))

    palavras_serp = set(re.findall(r'\w+', google_ctx.lower()))

    novas = palavras_artigo - palavras_serp

    score = min(len(novas) / 8, 100) # Matemático bruto

    return {"information_gain_score": round(score, 2), "palavras_unicas_trazidas": len(novas)}



def refinar_artigo_html(html_atual, instrucoes):

    """Permite que a IA edite apenas partes específicas de um artigo já gerado."""

    system = """Você é um Revisor Sênior e Editor de HTML.

    Sua tarefa é modificar um artigo HTML existente ESTRITAMENTE de acordo com as instruções do usuário.

    

    REGRAS CRÍTICAS:

    1. APLIQUE APENAS A MUDANÇA SOLICITADA. Não reescreva o tom de voz e não altere partes do texto que não foram mencionadas na instrução.

    2. MANTENHA TODO O CÓDIGO HTML INTACTO. Preserve todas as tags (<h1>, <h2>, <p>, <ul>), links (<a href...>) e imagens (<img>) exatamente como estão, a menos que a instrução peça para alterá-las.

    3. Retorne EXCLUSIVAMENTE o código HTML finalizado e completo. Pare de gerar texto imediatamente após a última tag HTML. Nada de introduções, comentários ou marcações (```html).

    """

    user = f"INSTRUÇÃO DE ALTERAÇÃO:\n{instrucoes}\n\nARTIGO ORIGINAL (HTML):\n{html_atual}"

    

    return chamar_llm(system, user, model="anthropic/claude-3.7-sonnet", temperature=0.2)



# ==========================================

# 4. MOTOR PRINCIPAL (COM AS TRAVAS E INCREMENTOS)

# ==========================================

def executar_geracao_completa(palavra_chave, marca_alvo, publico_alvo, conteudo_adicional="", conteudo_proprietario="", modo_humanizado=False, especialista_nome=None):

    df = st.session_state['brandbook_df']

    marca_info = df[df['Marca'] == marca_alvo].iloc[0].to_dict()

    url_marca = marca_info.get('URL', '')

    from datetime import datetime

    ano_atual = datetime.now().year



    # ROTEADOR DE CMS AQUI

    cms_url, cms_user, cms_pwd, cms_type = obter_credenciais_cms(marca_alvo)



    st.write(f"🕵️‍♂️ Fase 0: Buscando Google (Serper + Jina), IAs e RAG Reverso ({cms_type.upper()})...")

    

    # EXTRAI O ESTILO DO ESPECIALISTA SE ELE FOI SELECIONADO

    contexto_ghostwriting = ""

    if especialista_nome:

        st.write(f"👔 Lendo artigos do autor: {especialista_nome}...")

        contexto_ghostwriting = buscar_estilo_especialista(especialista_nome, st.session_state['especialistas_df'])

        

    with concurrent.futures.ThreadPoolExecutor() as executor:

        futuro_google = executor.submit(buscar_contexto_google, palavra_chave)

        futuro_ia = executor.submit(buscar_baseline_llm, palavra_chave)

        futuro_reverse = executor.submit(gerar_reverse_queries, palavra_chave)

        

        # O script decide qual CMS atacar

        if cms_type == "drupal":

            futuro_wp_rag = executor.submit(buscar_artigos_relacionados_drupal, palavra_chave, cms_url, cms_user, cms_pwd)

        else:

            futuro_wp_rag = executor.submit(buscar_artigos_relacionados_wp, palavra_chave, cms_url, cms_user, cms_pwd)

        

        try:

            contexto_google = futuro_google.result(timeout=45)

        except concurrent.futures.TimeoutError:

            contexto_google = "Aviso: A busca orgânica demorou muito. Conteúdo ignorado para manter a velocidade."

        try:

            baseline_ia = futuro_ia.result(timeout=45)

        except concurrent.futures.TimeoutError:

            baseline_ia = "Aviso: O motor de Baseline demorou muito a responder. Ignorado."

        try:

            reverse_queries = futuro_reverse.result(timeout=20)

        except:

            reverse_queries = "{}"

        try:

            contexto_wp = futuro_wp_rag.result(timeout=15)

        except:

            contexto_wp = "Erro de timeout ao buscar links internos."



    st.write("🔍 Fase 0.5: Analisando Entity Gap e Oportunidades Semânticas...")

    entity_gap = analisar_entity_gap(contexto_google, palavra_chave)



    st.write("🧠 Fase 1: Planejamento Editorial (GPT-4o)...")



    system_1 = """

Você é um Estrategista de Conteúdo GEO (LLM + Search) e Editor-Chefe orientado por E‑E‑A‑T.

Objetivo: produzir um briefing que entregue GANHO DE INFORMAÇÃO e fuja de estruturas genéricas.



REGRAS-MESTRAS (obrigatórias):

1) Nada de “definições básicas” ou “o que é”. O leitor já domina fundamentos. Busque ângulos originais e comparativos.

2) Zero jargão vazio. Frases curtas, voz ativa, tom assertivo.

3) Anti-alucinação total: só liste dados/estudos se houver URL pública verificável.

4) Neutralidade competitiva: ignore marcas privadas concorrentes presentes no contexto bruto.

5) Saída sempre em pt-BR.

6)GATILHOS DE VETO E ANTI-ALUCINAÇÃO (TOLERÂNCIA ZERO):

- REGRA DO DADO ÓRFÃO: É TERMINANTEMENTE PROIBIDO criar briefings sugerindo estatísticas exatas (ex: "37% de aumento", "9 em cada 10") a menos que você tenha a URL profunda e exata fornecida no contexto orgânico. Se não tiver a URL de pesquisa empírica, force o redator a focar em "Argumentação Lógica e Qualitativa" e proíba o uso de números absolutos ou percentuais.

- BLINDAGEM E LINK DE MARCA: Oriente o redator a usar a Marca Alvo exatamente como fornecida e a criar um link (href) para a URL Oficial da marca toda vez que ela for mencionada no texto.



ENTREGÁVEIS DO BRIEFING:

A) ÂNGULO NARRATIVO ÚNICO: escolha 1 (ex.: Quebra de Mito; Guia Tático; Análise de Tendência; Framework Operacional). Justifique em 2-3 linhas focado NAS DORES do público-alvo informado.

B) ESTRUTURA ANTI-FÓRMULA (H2): proponha 4 H2 provocativos, específicos e complementares (sem “O que é”, “Benefícios”, “Conclusão”).

C) MAPA DE EVIDÊNCIAS E DEEP LINKS: Você deve vasculhar o contexto orgânico fornecido para resgatar 2 a 3 DEEP LINKS REAIS. REGRA CRÍTICA: É ESTRITAMENTE PROIBIDO usar links de blogs de outras escolas privadas, colégios ou sistemas de ensino concorrentes (ex: Balão Vermelho, Bernoulli, etc.). Escolha APENAS links de autoridades neutras (Portais de Notícias como G1, revistas científicas, OCDE, PISA, MEC). Se não houver links neutros, não sugira nenhum.

E) ENTITY AUTHORITY GRAPH: Liste pelo menos 6 entidades institucionais relevantes para o tema para reforçar autoridade semântica.

F) GATILHO DE MARCA (SEM ALUCINAÇÃO): descreva como a marca aparecerá no terço final como um “Estudo de Caso Prático”. FOQUE APENAS na solução específica (o que a plataforma faz/metodologia). É EXPRESSAMENTE PROIBIDO inventar números de clientes (ex: "um grupo de 5 escolas"), inventar taxas de conversão ou cenários fictícios de antes/depois.

"""



    user_1 = f"""

Palavra-chave ou Consulta: '{palavra_chave}'



Público-Alvo Foco Deste Artigo: {publico_alvo}

    

CONTEÚDO ADICIONAL DO ESPECIALISTA (DIRECIONAMENTO HUMANO):

{conteudo_adicional if conteudo_adicional else "Nenhum conteúdo extra fornecido."}



Contexto extraído do Google (Serper + Jina):

{contexto_google}



Baseline de IAs (consenso atual):

{baseline_ia}



Reverse Queries (Perguntas de LLMs para estruturar o texto e FAQ):

{reverse_queries}



Marca Alvo: {marca_alvo}

URL da Marca: {url_marca}

- Posicionamento: {marca_info['Posicionamento']}

- Territórios Estratégicos: {marca_info['Territorios']}



Instruções:

- Construa o briefing completo seguindo as REGRAS-MESTRAS e ENTREGÁVEIS.

- Use as Reverse Queries para entender a intenção de busca profunda da IA.

- Se o contexto carecer de dados confiáveis com URL, declare FOCO CONCEITUAL (sem inventar números).

"""



    analise = chamar_llm(system_1, user_1, model="openai/gpt-4o", temperature=0.3)



    st.write("✍️ Fase 2: Redigindo em HTML Avançado (Claude 3.7 Sonnet)...")



    if modo_humanizado:

        st.write("✨ Modo Empático ativado: Focando em cadência humana e fluidez...")

        system_2 = """

Você é um Especialista em SEO Semântico (GEO) e um profissional de educação/gestão com vasta experiência prática. 

Sua missão é traduzir o Tom de Voz corporativo em um texto que não pareça um artigo de blog encomendado, mas sim um relato ou análise de quem vive a realidade educacional diariamente.



1. A VOZ DA TRINCHEIRA (EXPERIÊNCIA REAL):

- Escreva como alguém que já participou de reuniões tensas com mantenedores, ouviu reclamações de pais e acompanhou dinâmicas reais de sala de aula. 

- Evite a empatia genérica e enlatada de IA (Ex: NUNCA use "Sabemos que gerir uma escola é um desafio..."). Vá direto para o problema real.

- IMPERFEIÇÃO HUMANA CONTROLADA: A cadência deve parecer orgânica. Não tente fechar todos os parágrafos com uma conclusão perfeita ou "redonda". Use transições secas. Textos humanos reais têm cortes e vão direto ao ponto.



2. O DETECTOR DE ROBÔS E CLICHÊS (BLACKLIST ABSOLUTA):

- VETO A FRASES DE IMPACTO GENÉRICAS: Se usar uma frase curta, ela deve trazer INFORMAÇÃO, não drama. Estão TERMINANTEMENTE PROIBIDAS as frases: "Os números não mentem", "Esta é uma falsa dicotomia", "O segredo está em", "Estamos diante de".

- VETO DE VOCABULÁRIO "IA": Jamais use: "no cenário atual", "cada vez mais", "divisor de águas", "é inegável que", "neste artigo veremos", "em resumo", "por fim", "transcendeu".



3. ANCORAGEM NO MUNDO REAL (CRÍTICO PARA INDETECTABILIDADE):

- MEMÓRIA OPERACIONAL: Sempre que explicar um conceito teórico, obrigatoriamente "encoste a ideia na realidade" com uma micro-cena plausível (Ex: um professor lidando com celulares no fundo da sala, uma decisão financeira no meio do semestre, o momento da renovação de matrículas).

- DETALHE IMPERFEITO: Inclua pequenos detalhes contextuais em suas explicações que não são essenciais para o argumento central, mas gritam "fator humano" (ex: "em turmas mais agitadas", "na primeira semana de provas", "quando o sistema trava").

- FRICÇÃO ANALÍTICA: O texto não pode ser um mar de positividade. Em pelo menos um H2, questione uma prática comum do mercado, aponte um efeito colateral inesperado ou discorde do senso comum. Mostre atrito intelectual.



4. ESTRUTURA GEO INVISÍVEL E SEO:

- CONCEITO FLUIDO: Logo no início, entregue o conceito da palavra-chave em um parágrafo normal, sem usar etiquetas como "Definição:".

- RESPOSTA RÁPIDA: Crie um <h2>Resposta rápida para: [palavra-chave]</h2>. Abaixo dele, responda a dúvida principal em 2 ou 3 linhas narrativas e diretas.

- SÍNTESE VISUAL: Insira a tag exata `<br>Resumo Estratégico<br>` e crie um <ul> com 3 a 5 bullet points valiosos. Limite absoluto de 2 listas no artigo todo.

- CITAÇÃO NATURAL: Inclua a visão de um especialista começando o parágrafo de forma orgânica, como: <p><strong>A visão dos especialistas:</strong> ...</p>



5. REGRAS DE LINKAGEM E BLINDAGEM E-E-A-T (TOLERÂNCIA ZERO):

- VETO TOTAL A RIVAIS: É ESTRITAMENTE PROIBIDO citar o nome ou link de QUALQUER outra escola privada ou sistema de ensino concorrente no Brasil (ex: Balão Vermelho, Anglo, Bernoulli). Ignore-os se aparecerem na pesquisa. A única marca privada permitida é a [Marca Alvo].

- LINK DA MARCA: Sempre que citar a [Marca Alvo], transforme-a num link HTML OBRIGATÓRIO: <a href="[URL_DA_MARCA]" target="_blank">[NOME_DA_MARCA]</a>.

- RASTREABILIDADE (DEEP LINKS): Use os links externos fornecidos no briefing (MEC, OCDE, Portais de Notícias). Ancore-os naturalmente. Se não tiver a URL real fornecida no briefing para um dado/pesquisa, NÃO cite a instituição ou os números. Evite alucinação de fontes.

- RAG REVERSO (LINKS INTERNOS): Você receberá "ARTIGOS INTERNOS DISPONÍVEIS". É uma exigência técnica inegociável inserir hiperlinks <a> para 1 ou 2 desses artigos no meio do seu texto, de forma natural.



6. DIRECIONAMENTO E HTML:

- BÚSSOLA DO ARTIGO: Absorva o bloco "Conteúdo Adicional" (teorias, autores). Expanda esses elementos com seu conhecimento interno, aplicando a memória operacional e a fricção analítica descritas acima.

- ESTUDO DE CASO: Ao falar da solução da [Marca Alvo], não faça um texto de vendas. Mostre o contexto operacional de como a ferramenta/método deles destravou um problema.

- REGRAS TÉCNICAS: Use APENAS <h1>, <h2>, <h3>, <p>, <ul>, <ol>, <li>, <strong>, <a>. O <h1> DEVE TER NO MÁXIMO 60 CARACTERES. Títulos em "Sentence case" (Maiúscula só no início).



Finalize o texto com um corte seco ou uma última reflexão técnica. É rigorosamente proibido usar parágrafos de conclusão clichês. Pare de gerar texto imediatamente após fechar a última tag HTML.

"""

    else:

        st.write("⚙️ Modo GEO Restrito ativado: Focando em compliance estrutural...")

        system_2 = """        

Você é Especialista em SEO Semântico (GEO), Copywriter Sênior e Redator de Autoridade E‑E‑A‑T.

Sua missão é traduzir o Tom de Voz corporativo em um texto altamente engajador, focando cirurgicamente nas dores e aspirações do público-alvo.



MANIFESTO ANTI-ROBÔ E ESTILO DA MARCA:

1) Incorpore RIGOROSAMENTE o Tom de Voz e a essência da marca informada.

1.2) Fale DIRETAMENTE com o Público-Alvo definido. Entenda a realidade deles (ex: um gestor busca eficiência; pais buscam segurança).

1.3) Ritmo, profundidade e elegância. Voz ativa. Evite enchimento.

2) PROIBIDO usar jargões de IA como: "No cenário atual", "Cada vez mais", "É inegável que", "É importante ressaltar", "Neste artigo veremos", "Em resumo", "Por fim". 

2.1) VETO DE VOCABULÁRIO IA APRIMORADO (BLACKLIST ABSOLUTA): Estão permanentemente banidas do seu vocabulário as seguintes expressões e suas variações: "cenário em transformação", "transcendeu o status", "mundo globalizado", "mundo contemporâneo", "não é apenas X, mas também Y", "mergulhar em", "verdadeiro divisor de águas", "é fundamental notar", "revolucionar".

2.2) ESTILO JORNALÍSTICO (SHOW, DON'T TELL): Não diga que algo é "inovador" ou "fundamental". Apresente o fato técnico e deixe o leitor concluir isso. Escreva como um analista de dados da McKinsey ou um jornalista investigativo focado em negócios B2B.

3) Não explique o óbvio; entregue leitura avançada.

4) LINK OFICIAL DA MARCA (OBRIGATÓRIO): A marca alvo e sua URL serão enviadas a você. Toda vez que você citar o nome da marca no texto, você É OBRIGADO a transformá-la em um hiperlink para o site oficial. Exemplo: <a href="[URL_AQUI]" target="_blank">[NOME_DA_MARCA]</a>.



GEO (GENERATIVE ENGINE OPTIMIZATION) E CHUNK CITABILITY – REGRAS OBRIGATÓRIAS:

4) BLOCO DE DEFINIÇÃO ORGÂNICA (SEM ETIQUETAS): Logo no início do texto, você DEVE explicar o conceito central da palavra-chave em menos de 30 palavras. Faça isso de forma natural e fluida no meio de um parágrafo. É ESTRITAMENTE PROIBIDO usar etiquetas robóticas como "Definição:" ou "O que é:". Apenas explique o conceito grifando o termo em negrito.

5) ANSWER ANCHOR (RESPOSTA RÁPIDA SUAVIZADA): Logo após a introdução, crie um <h2>Resposta rápida para: [insira a palavra-chave]</h2>. Abaixo deste H2, entregue a resposta direta e mastigada em no máximo 2 linhas. NÃO USE etiquetas como "Resposta direta:". Apenas escreva o parágrafo indo direto ao ponto, como um jornalista experiente faria.

6) RESUMO ESTRATÉGICO: Insira exatamente a linha `<br>Resumo Estratégico<br>` e crie um <ul> com 3 a 5 bullet points centrais e altamente informativos.

7) FRAMEWORK E LEITURA ESCANEÁVEL (CHUNK CITABILITY COM ASSIMETRIA EXTREMA): Transforme seções em frameworks estruturados. O limite MÁXIMO de um parágrafo é de 4 linhas (aprox. 35 palavras). É OBRIGATÓRIO QUEBRAR A SIMETRIA: Intercale parágrafos "maiores" (25 a 35 palavras) com parágrafos de impacto ultracurtos formados por UMA ÚNICA FRASE (8 a 15 palavras). É TERMINANTEMENTE PROIBIDO que os parágrafos tenham o mesmo tamanho visual. LIMITAÇÃO DE LISTAS: Use no máximo 2 a 3 listas (<ul>) em todo o artigo.

8) MICRO BLOCO DE AUTORIDADE: Inclua: <p><strong>Segundo especialistas:</strong> ...</p> ancorado com dados factuais ou conceitos sólidos.



REGRAS HTML E FORMATAÇÃO VISUAL (CRÍTICAS E ABSOLUTAS):

9) Use exclusivamente HTML puro: <h1>, <h2>, <h3>, <p>, <ul>, <ol>, <li>, <strong>, <a>. Sem Markdown ou <img>.

10) O primeiro caractere DEVE ser <h1> e o último DEVE ser o fechamento da última tag HTML. O título <h1> DEVE TER NO MÁXIMO 60 CARACTERES (cerca de 6 a 8 palavras) para não ser cortado no Google. Seja criativo, mas extremamente conciso.

11) REGRA DE CAPITALIZAÇÃO (SENTENCE CASE): É ESTRITAMENTE PROIBIDO usar "Title Case" nos títulos H1, H2 e H3. Use o padrão gramatical brasileiro: APENAS a primeira letra da frase e nomes próprios/marcas devem ser maiúsculos (Ex: "Como a tecnologia ajuda escolas", NUNCA "Como A Tecnologia Ajuda Escolas").

12) PROIBIDO PARÁGRAFOS SIMÉTRICOS: Verifique o texto antes de entregar. Se você notar que os parágrafos estão visualmente do mesmo tamanho, fragmente-os imediatamente. Obrigatoriamente inclua frases isoladas para criar respiros visuais profundos.

13) VARIAÇÃO HUMANA DE RITMO (OBRIGATÓRIO E EXTREMO):

Humanos não escrevem com ritmo perfeitamente regular. Introduza variação natural drástica:

- Misture frases normais com frases de altíssimo impacto e curtas.

- É OBRIGATÓRIO que a estrutura visual do texto oscile entre blocos maiores e blocos bem curtos.

14) LISTAS COM CONTEXTO E LIMITE: O texto não pode parecer uma apresentação de slides. Se usar uma lista (respeitando o limite máximo de 3 no texto todo), é obrigatório introduzi-la com contexto e concluí-la com forte interpretação analítica.



REGRAS DE LINKAGEM, FONTES E VETOS (E-E-A-T):

15) VETO TOTAL A RIVAIS E OUTRAS ESCOLAS (CRÍTICO): É ESTRITAMENTE PROIBIDO citar o nome ou inserir hiperlinks para QUALQUER outra escola privada, colégio ou sistema de ensino concorrente no Brasil ou no mundo (ex: Balão Vermelho, Anglo, Bernoulli, etc.). Se o contexto do Google trouxer o blog de uma escola, IGNORE-O. A única marca privada do setor educacional que pode ser citada é a Marca Alvo.

16) PROTOCOLO DE RASTREABILIDADE (DEEP LINKS OBRIGATÓRIOS): É OBRIGATÓRIO incluir pelo menos 2 a 3 links externos (<a href="..." target="_blank">) ancorando afirmações ou dados. 

17) VETO AO LAZY LINKING: É ESTRITAMENTE PROIBIDO linkar para homepages genéricas (ex: "onu.org", "ibge.gov.br"). Todo link DEVE ser um DEEP LINK (URL completa e específica que leva direto à página do estudo/artigo citado, contendo slugs visíveis).

18) FONTES NEUTRAS E DEEP LINKING: Todo link externo deve ir para páginas específicas (slugs longos), nunca homepages genéricas. Os links externos DEVEM ser exclusivamente de órgãos oficiais (MEC, OCDE), institutos de pesquisa ou portais de notícias sérios (G1, Porvir). Jamais faça link building para blogs de outras escolas.

19) FONTE DOS LINKS (PROIBIDO ALUCINAR URL): Use EXCLUSIVAMENTE os deep links que foram explicitamente fornecidos no briefing. É ESTRITAMENTE PROIBIDO inventar, adivinhar ou construir URLs da sua própria memória (ex: criar links falsos da SciELO, DOIs falsos, ou caminhos fictícios de universidades). Se o briefing não te fornecer uma URL válida e real, você está liberado da obrigação de colocar links externos. Nesse caso, apenas foque na argumentação conceitual, MAS NÃO CITE o nome do estudo/instituição para não quebrar a Regra de Ouro dos Dados Citados abaixo.

20) REGRA DE OURO DOS DADOS CITADOS (ANTI-PENALIZAÇÃO): É ESTRITAMENTE PROIBIDO citar o nome de associações, institutos, pesquisas ou dados numéricos de mercado (ex: Associação Brasileira de Ensino Bilíngue, IBGE, OMS) sem ancorar a citação em um link (<a href="...">). Se você não tiver o link externo real para inserir, NÃO CITE o nome da instituição ou o dado; reescreva a frase de forma puramente conceitual. Exceção: Dados institucionais da própria Marca Alvo não precisam de link.

21) LINKAGEM INTERNA (OBRIGAÇÃO ABSOLUTA): Você receberá uma lista chamada "ARTIGOS INTERNOS DISPONÍVEIS". É UMA EXIGÊNCIA INEGOCIÁVEL que você escolha de 1 a 2 artigos dessa lista e crie links HTML (<a href="[URL]">) no meio do seu texto. As URLs dessa lista são 100% seguras e validadas, use-as sem medo para criar autoridade de nicho.



ESTRATÉGIA EDITORIAL, NARRATIVA E VOZ:

22) DIRECIONAMENTO ESTRATÉGICO DO ESPECIALISTA (BÚSSOLA DO ARTIGO): O usuário pode fornecer um bloco de "Conteúdo Adicional" contendo teorias, autores, insumos próprios ou links. Você não precisa fazer um "copia e cola" literal e engessado, mas DEVE usar esses elementos como a base principal da sua argumentação. Use seu conhecimento interno para expandir as teorias ou autores citados, aprofunde os conceitos sugeridos e costure essas referências de forma fluida e inteligente para enriquecer o texto.

23) FRAMEWORK DO ESTUDO DE CASO (P.A.R.): O seu "Estudo de Caso" não pode parecer um panfleto publicitário. Ele deve ser escrito na estrutura Problema (qual dor técnica havia) > Ação da Marca (qual tecnologia exata foi usada) > Resultado (o ganho institucional listado no brandbook). Use o nome comercial da marca.

24) ENTITY SATURATION: Integre naturalmente as entidades mapeadas para provar domínio do nicho.

25) VOZ EDITORIAL DE ANALISTA: Escreva como um analista que observa padrões do setor educacional.

26) OBSERVAÇÃO OPERACIONAL (ANTI-TEXTO GENÉRICO):

-Sempre que explicar um conceito , inclua uma observação concreta da situação ou implementação.

-Evite abstrações vagas. Prefira descrições operacionais.

27) CONTRAPONTO ANALÍTICO (OBRIGATÓRIO EM PELO MENOS 1 H2):

Inclua pelo menos um momento do texto onde uma crença comum do setor é questionada ou refinada.

28) MICRO-ANÁLISE CAUSAL:

Sempre que apresentar um benefício ou prática, explique rapidamente o mecanismo por trás.

29) MICRO-SÍNTESE:

Após alguns blocos analíticos, inclua uma frase curta que consolide a ideia.

"""



    user_2 = f"""

Palavra-chave ou Consulta: '{palavra_chave}'



CONTEXTO TEMPORAL: Ano de {ano_atual}. Não projete o futuro sem evidência.

    

CONTEÚDO ADICIONAL DO ESPECIALISTA (DIRECIONAMENTO HUMANO OBRIGATÓRIO):

{conteudo_adicional if conteudo_adicional else "Nenhum conteúdo extra fornecido. Siga apenas o briefing."}



CONTEÚDO PROPRIETÁRIO INEGOCIÁVEL (COPIAR E COLAR EXATAMENTE COMO ESTÁ):

{conteudo_proprietario if conteudo_proprietario else "Nenhum conteúdo proprietário exigido."}

ATENÇÃO: Se houver texto no bloco acima, você é OBRIGADO a encontrar um espaço lógico no artigo e transcrever essa frase ou bloco de texto LITERALMENTE, palavra por palavra, sem resumir ou alterar nenhuma vírgula.



O QUE A CONCORRÊNCIA DIZ HOJE:

{contexto_google}



SEU BRIEFING (siga à risca o ângulo e integre o Entity Authority Graph):

{analise}



DIRECIONAMENTO DE COPYWRITING E MARCA:

- Público-Alvo Deste Texto (Foque toda a narrativa neles): {publico_alvo}

- Tom de Voz Exigido: {marca_info['TomDeVoz']}

- Marca Alvo: {marca_alvo}

- URL da Marca: {url_marca} (OBRIGATÓRIO: Linkar a marca para esta URL sempre que citada).

- Posicionamento: {marca_info['Posicionamento']}

- Territórios: {marca_info['Territorios']}

- Diretrizes OBRIGATÓRIAS: {marca_info.get('RegrasPositivas', '')}

- O que NÃO fazer: {marca_info['RegrasNegativas']}



ARTIGOS INTERNOS DISPONÍVEIS (RAG REVERSO):

Você DEVE obrigatoriamente usar pelo menos um destes links como hiperlink no meio do texto, linkando de forma natural as palavras-chave relacionadas.

{contexto_wp}



<checklist_de_seguranca_obrigatorio>

1. A sua "Resposta rápida" está bem no início do texto e é super objetiva?

2. A sua "Definição" tem menos de 30 palavras? (Se tiver mais, reduza agora).

3. ASSIMETRIA VISUAL: Você quebrou os parágrafos corretamente? Há frases isoladas servindo como parágrafos curtos misturadas com parágrafos de 3 linhas? Se o texto estiver um "bloco de tijolo" igual, altere agora.

4. Você usou todas as entidades obrigatórias mapeadas no briefing?

5. VETO A ESCOLAS E RIVAIS: Verifique seu texto e as URLs dos seus links (<a href="...>). Você citou o nome ou o site de ALGUMA OUTRA ESCOLA PRIVADA ou sistema de ensino que não seja a {marca_alvo}? SE SIM, remova imediatamente.

6. O seu "Estudo de Caso" foca na tecnologia/metodologia real da {marca_alvo}? Verifique se você inventou historinha de cliente fictício ou números falsos. Se sim, APAGUE ISSO.

7. CHECK DE DEEP LINKS: Você incluiu pelo menos 2 links externos? Olhe para as URLs dentro do <a href>. Elas são DEEP LINKS reais? Se usou página inicial, substitua IMEDIATAMENTE por um deep link específico ou apague o link.

8. Você garantiu que TODAS as menções à {marca_alvo} contêm o link <a href="{url_marca}">?

8.1 VERIFICAÇÃO DE RAG: Leia o seu texto final. Você incluiu a tag <a href="..."> usando as URLs da lista de Artigos Internos Disponíveis? Se não, insira.

9. Você checou a existência de dados numéricos no briefing? Se não houver, garanta que sua abordagem é conceitual e livre de alucinações matemáticas.

10. AUDITORIA DE FONTES (TOLERÂNCIA ZERO): Você citou alguma Associação, Instituto, Estudo, Pesquisa, Ministério no texto? Se sim, a tag de link (<a href="...">) está EXATAMENTE junto ao nome deles? Se estiver sem link, APAGUE a frase inteira imediatamente.

11. Você analisou o "CONTEÚDO ADICIONAL DO ESPECIALISTA"? O artigo reflete as ideias, autores ou referências sugeridas ali de forma natural e profunda?

12. O seu título <h1> tem menos de 60 caracteres? Conte as letras.

13. CONTEÚDO PROPRIETÁRIO (CRÍTICO): Verifique se foi fornecido algum "CONTEÚDO PROPRIETÁRIO INEGOCIÁVEL". Se sim, procure no seu texto gerado. A frase está EXACTAMENTE igual ao original, sem nenhuma palavra alterada? Se você resumiu ou alterou a frase, corrija agora colando a frase original.

</checklist_de_seguranca_obrigatorio>

14. DIRETRIZ DE GHOSTWRITING E AUTORIA (CRÍTICO):{contexto_ghostwriting if contexto_ghostwriting else "Nenhum autor específico selecionado. Use o tom da marca padrão."}

ATENÇÃO: Se o bloco acima contiver artigos de um especialista, você assumirá a IDENTIDADE dele. Absorva o vocabulário, o ritmo e o nível de formalidade que ele usa nos artigos fornecidos. Integre o seu conhecimento sobre a palavra-chave com os conceitos que ele costuma defender. 



Escreva o ARTIGO FINAL em HTML conforme as regras GEO, preservando exatamente os marcadores:

<br>Resumo Estratégico<br>

<br>Perguntas Frequentes<br>



ATENÇÃO: Pare de escrever IMEDIATAMENTE após a última tag HTML. NUNCA gere auto-avaliações, comentários ou textos que comecem com "AI:".

"""

    artigo_html = chamar_llm(system_2, user_2, model="anthropic/claude-3.7-sonnet", temperature=0.45)

    artigo_html = re.sub(r'^```html\n|```$', '', artigo_html, flags=re.MULTILINE).strip()

    

    # GUILHOTINA PYTHON: Corta qualquer "auto-avaliação" da IA que venha depois do fechamento do HTML

    if '<' in artigo_html and '>' in artigo_html:

        artigo_html = artigo_html[artigo_html.find('<') : artigo_html.rfind('>') + 1]



    st.write("🛠️ Fase 3: Extraindo JSON e Metadados via Pydantic...")

    schema_gerado = MetadadosArtigo.model_json_schema() if hasattr(MetadadosArtigo, "model_json_schema") else MetadadosArtigo.schema_json()



    system_3 = f"""

Você é especialista em SEO técnico e Schema.org.

Retorne EXCLUSIVAMENTE **um JSON** puro, válido e COMPATÍVEL com este schema Pydantic:

{json.dumps(schema_gerado, ensure_ascii=False)}



REGRAS CRÍTICAS:

1) NUNCA inclua markdown, comentários, ```json ou campos extras.

2) 'title': 45–60 caracteres (otimizado para H1/SEO, sem marca).

3) 'meta_description': 130–150 caracteres (promessa clara + gancho, sem clickbait).

4) 'dicas_imagens': exatamente 2 strings em inglês, MUITO CURTAS E SIMPLES (máximo 1 a 2 palavras, ex.: "classroom", "students", "school"). É ESTRITAMENTE PROIBIDO gerar frases longas. Termos longos quebram a busca da API.

5) 'schema_faq': JSON-LD **FAQPage** com @context "[https://schema.org](https://schema.org)", @type "FAQPage" e mainEntity como lista de objetos Question/acceptedAnswer.

    - As perguntas e respostas DEVEM ser extraídas **textualmente** da seção “Perguntas Frequentes” presente no HTML fornecido (mesma grafia e sentido).

    - Se não houver FAQ no HTML, retorne 'schema_faq': {{}}. 



ANTI-CLOAKING E VALIDAÇÃO:

- Proibido inventar perguntas/respostas que não existam no HTML.

- Proibido inventar dados/anos/links no JSON.

- Saída deve conter apenas as chaves: title, meta_description, dicas_imagens, schema_faq.

"""



    user_3 = f"HTML COMPLETO:\n{artigo_html}"



    dicas_json = chamar_llm(system_3, user_3, model="anthropic/claude-3.7-sonnet", temperature=0.1, response_format={"type": "json_object"})



   # MOTOR DUPLO DE IMAGENS (UNSPLASH + FALLBACK POLLINATIONS)

    try:

        json_limpo = dicas_json.strip().removeprefix('```json').removesuffix('```').strip()

        meta_dicas = json.loads(json_limpo)

        termos_busca = meta_dicas.get('dicas_imagens', [])

        UNSPLASH_KEY = st.secrets.get("UNSPLASH_KEY", "")

        

        if isinstance(termos_busca, list):

            for i, termo in enumerate(termos_busca[:2]):

                img_html_pronta = ""

                if UNSPLASH_KEY:

                    # URL LIMPA E DIRETA

                    url = f"https://api.unsplash.com/search/photos?query={urllib.parse.quote(termo)}&client_id={UNSPLASH_KEY}&per_page=1&orientation=landscape"

                    try:

                        res = requests.get(url, timeout=5)

                        if res.status_code == 200:

                            dados_img = res.json()

                            if "results" in dados_img and len(dados_img["results"]) > 0:

                                img_url = dados_img["results"][0]["urls"]["regular"]

                                alt_text = dados_img["results"][0]["alt_description"] or termo

                                img_html_pronta = f'<img src="{img_url}" alt="{alt_text}" style="width:100%; border-radius:8px;" loading="lazy" decoding="async" />'

                    except Exception:

                        pass

                

                if not img_html_pronta:

                    # FALLBACK LIMPO E DIRETA

                    clean_termo = str(termo).replace("'", "").replace('"', '').strip()

                    p_codificado = urllib.parse.quote(clean_termo)

                    base_poll = "https://image.pollinations.ai/prompt/"

                    img_html_pronta = f'<img src="{base_poll}{p_codificado}?width=1024&height=512&nologo=true&model=flux" alt="{clean_termo}" style="width:100%; border-radius:8px;" loading="lazy" decoding="async" />'

                    

                if img_html_pronta:

                    alvo_replace = '<br>Resumo Estratégico<br>' if i == 0 else '<br>Perguntas Frequentes<br>'

                    artigo_html = artigo_html.replace(alvo_replace, f'{img_html_pronta}\n{alvo_replace}', 1)

    except Exception as e:

        st.error(f"Erro ao injetar imagem: {e}") # Mudei para st.error para você ver se falhar



    # CHAMADAS INCREMENTAIS PÓS-REDAÇÃO (GEO PIPELINE COMPLETO)

    st.write("📊 Fase 4: Calculando Originalidade, Citabilidade GEO e Cluster...")

    score_originalidade = avaliar_originalidade(artigo_html, contexto_google)

    citabilidade = prever_citabilidade_llm(artigo_html, palavra_chave)

    cluster = gerar_cluster(palavra_chave)

    citation_score = calcular_citation_score(artigo_html)



    st.write("🧪 Fase 5: Calculando Matrizes RAG e Entity Coverage...")

    entity_coverage = calcular_entity_coverage(artigo_html, entity_gap)

    

    geo_score = calcular_geo_score_matematico(citation_score, score_originalidade, citabilidade, entity_coverage)

    chunk_citability = avaliar_chunk_citability(artigo_html)

    answer_first = avaliar_answer_first(artigo_html)

    rag_chunks = simular_rag_chunks(artigo_html, palavra_chave)

    evidence_density = calcular_evidence_density(artigo_html)

    information_gain = calcular_information_gain(artigo_html, contexto_google)



    st.write("🔬 Fase 6: Simulação de RAG e Citation Hijacking (Motores LLM)...")

    retrieval_simulation = simular_llm_retrieval(palavra_chave, artigo_html)

    hijacking_risk = detectar_citation_hijacking(artigo_html)

    ai_simulation = simular_resposta_ai(palavra_chave, artigo_html)



    return (

        artigo_html, dicas_json, contexto_google, baseline_ia, entity_gap, 

        score_originalidade, citabilidade, cluster, reverse_queries, 

        citation_score, entity_coverage, geo_score, retrieval_simulation, 

        hijacking_risk, ai_simulation, chunk_citability, answer_first, 

        rag_chunks, evidence_density, information_gain, contexto_wp

    )



def publicar_wp(titulo, conteudo_html, meta_dict, wp_url, wp_user, wp_pwd):

    import base64

    

    seo_title = meta_dict.get("title", titulo)

    meta_desc = meta_dict.get("meta_description", "")

    

    # Payload limpo sem scripts

    payload = {

        "title": titulo,

        "content": conteudo_html,

        "status": "draft",

        "meta": {

            "_yoast_wpseo_title": seo_title,

            "_yoast_wpseo_metadesc": meta_desc

        }

    }

    

    wp_pwd_clean = wp_pwd.replace(" ", "").strip()

    credenciais = f"{wp_user}:{wp_pwd_clean}"

    token_auth = base64.b64encode(credenciais.encode('utf-8')).decode('utf-8')

    

   # MÁSCARA ROBUSTA: Disfarce de navegador real (Chrome no Windows)

    headers = {

        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',

        'Accept': 'application/json, text/plain, */*',

        'Content-Type': 'application/json',

        'Authorization': f'Basic {token_auth}',

        'Connection': 'keep-alive',

        'Accept-Encoding': 'gzip, deflate, br'

    }

    

    try:

        response = requests.post(wp_url, json=payload, headers=headers, timeout=30)

        return response

    except Exception as e:

        class ErrorResponse:

            status_code = 500

            text = f"Erro interno de conexão: {str(e)}"

            def json(self): return {}

        return ErrorResponse()



def publicar_drupal(titulo, conteudo_html, meta_dict, d_url, d_user, d_pwd):

    import base64
