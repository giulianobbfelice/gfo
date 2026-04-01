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
import base64
import os

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E FUNÇÕES DE UI
# ==========================================
st.set_page_config(page_title="GFO | Machine GEO", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

# Função para carregar a logo local
@st.cache_data
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""

# CARREGUE SUA LOGO AQUI
logo_b64 = get_base64_of_bin_file("file.svg")
logo_data_uri = f"data:image/svg+xml;base64,{logo_b64}" if logo_b64 else ""

# Lógica de Navegação via Query Parameters (Mais estável que botões)
query_params = st.query_params
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = query_params.get("page", "Gerador de Artigos")
if 'show_inputs' not in st.session_state:
    st.session_state['show_inputs'] = False

# ==========================================
# ESTILOS GLOBAIS
# ==========================================
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Montserrat:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    h1, h2, h3 {{
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        color: #111827 !important;
        letter-spacing: -0.02em;
    }}

    /* ESCONDER COMPONENTES NATIVOS DO STREAMLIT */
    [data-testid="stSidebar"], header[data-testid="stHeader"] {{ display: none !important; }}
    .block-container {{ padding-top: 1rem; max-width: 1200px; }}

    .gfo-tag {{
        display: inline-flex;
        align-items: center;
        background-color: #E8Faf2; /* Fundo verde clarinho */
        color: #4ED1A3 !important;
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
        padding: 6px 16px;
        border-radius: 50px;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }}

    /* === 1. MENU PRINCIPAL COM LOGO ALINHADA === */
    div[data-testid="stTabs"]:first-of-type > div > div[data-baseweb="tab-list"] {{
        gap: 24px;
        border-bottom: 2px solid #E5E7EB;
        padding-left: 170px;
        position: relative;
    }}
    
    /* Injeta a Logo GFO local na barra */
    div[data-testid="stTabs"]:first-of-type > div > div[data-baseweb="tab-list"]::before {{
        content: "";
        background-image: url('{logo_data_uri}');
        background-size: contain;
        background-repeat: no-repeat;
        background-position: left center;
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 140px;
        height: 60px;
    }}
    
    div[data-testid="stTabs"]:first-of-type > div > div[data-baseweb="tab"] {{
        font-family: 'Montserrat', sans-serif;
        font-weight: 600;
        color: #6B7280;
        padding-top: 16px;
        padding-bottom: 16px;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    div[data-testid="stTabs"]:first-of-type > div > div[data-baseweb="tab"][aria-selected="true"] {{
        color: #111827 !important;
        border-bottom: 3px solid #4ED1A3 !important; /* Verde GFO */
        background: transparent !important;
    }}

    /* === 2. TODOS OS BOTÕES PRIMÁRIOS === */
    div[data-testid="stButton"] > button[kind="primary"] {{
        background-color: #111827 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 24px !important;
        font-family: 'Inter', sans-serif;
        font-weight: 600 !important;
        height: 3.2em;
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}
    div[data-testid="stButton"] > button[kind="primary"]:hover {{
        background-color: #374151 !important;
        transform: translateY(-2px) !important;
    }}
    div[data-testid="stButton"] > button[kind="primary"] *,
    div[data-testid="stButton"] > button[kind="primary"] p {{
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        -webkit-text-stroke: 0px transparent !important;
        text-shadow: none !important;
    }}

    /* === 3. BOTÃO HERÓI CIRCULAR DA HOME === */
    div[data-testid="stElementContainer"]:has(.hero-btn-hook) + div[data-testid="stElementContainer"] div[data-testid="stButton"] > button[kind="primary"] {{
        border-radius: 50px !important;
        height: 54px !important;
    }}

    /* ESTILO DOS CARDS DE VENDA */
    .saas-card {{
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 24px;
        height: 100%;
        transition: transform 0.2s, box-shadow 0.2s;
    }}
    .saas-card:hover {{
        transform: translateY(-5px);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        border-color: #D1D5DB;
    }}
    .card-title {{
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        font-size: 1.1rem;
        color: #111827;
        margin-bottom: 8px;
    }}
    .card-text {{
        font-size: 0.9rem;
        color: #4B5563;
        line-height: 1.5;
    }}

    /* PIPELINE STYLING */
    .pipeline-container {{
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
    }}
    .pipeline-step {{
        cursor: help; 
        color: #374151;
        font-weight: 500;
        transition: color 0.2s;
    }}
    .pipeline-step:hover {{ color: #4ED1A3; }} /* Verde GFO */

    /* BOTÃO FLUTUANTE DE AJUDA (DIREITA) */
    .floating-help-container {{
        position: fixed;
        bottom: 40px;
        right: 40px;
        z-index: 99999;
    }}
    div[data-testid="stPopover"] > button {{
        background-color: #4ED1A3 !important; /* Verde GFO */
        color: white !important;
        border-radius: 50% !important;
        width: 65px !important;
        height: 65px !important;
        border: none !important;
        box-shadow: 0 10px 15px -3px rgba(78, 209, 163, 0.4) !important;
        display: flex;
        justify-content: center;
        align-items: center;
        transition: transform 0.2s;
        padding: 0 !important;
        margin: 0 !important;
    }}
    div[data-testid="stPopover"] > button:hover {{
        transform: scale(1.1);
        background-color: #3BBF91 !important; /* Verde GFO Hover (Pantone 339C approx) */
    }}
    div[data-testid="stPopover"] > button p {{
        font-size: 28px !important;
        font-weight: bold;
        margin: 0 !important;
        color: white !important;
    }}
    /* Remove as bordas e fundos dos botões do menu */
    div[data-testid="stButton"] > button[kind="secondary"] {{
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1.1 MENU DE NAVEGAÇÃO SAAS NO TOPO
# ==========================================
nav_cols = st.columns([2, 2, 2, 2, 2, 2])

with nav_cols[0]:
    if logo_data_uri:
        st.markdown(f'<img src="{logo_data_uri}" style="width: 50px; margin-top: -5px;" alt="Logo GFO">', unsafe_allow_html=True)
    else:
        st.markdown('<h3>GFO</h3>', unsafe_allow_html=True)

opcoes_menu = ["Gerador de Artigos", "BrandBook", "Monitor de GEO", "Revisor de GEO", "Auditor de Artigos"]

try:
    index_selecionado = opcoes_menu.index(st.session_state['current_page'])
    st.markdown(f"""
    <style>
    div[data-testid="stHorizontalBlock"]:first-of-type div[data-testid="stColumn"]:nth-child({index_selecionado + 2}) button {{
        color: #111827 !important; 
        -webkit-text-stroke: 0.6px #111827 !important;
        border-bottom-color: #4ED1A3 !important;
    }}
    </style>
    """, unsafe_allow_html=True)
except ValueError:
    pass

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
    st.markdown("Bem-vindo. Este motor funciona como sua **equipe particular de especialistas**. Ele espiona a concorrência, entende as regras do Google e das IAs, e escreve conteúdos usando a voz exata da sua marca.")
    
    with st.expander("🚀 Como usar as 5 Abas?"):
        st.markdown("""
        **1. Gerador:** Cria artigos completos do zero. Você dá o tema (e links de referência se quiser), ele pesquisa o mercado e redige.
        
        **2. Brandbook:** O 'cérebro' do sistema. É aqui que dizemos o que cada marca pode ou não falar.
        
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
    dicas_imagens: list[str] = Field(..., description="Lista com 2 prompts curtos EM INGLÊS para buscar imagens (ex: ['futuristic server room', 'business meeting'])")
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
# 2. BRANDBOOK EMBUTIDO GENÉRICO
# ==========================================
if 'brandbook_df' not in st.session_state:
    dados_iniciais = [
        {
            "Marca": "Generic Corp",
            "URL": "https://www.genericcorp.com/",
            "Posicionamento": "Marca visionária e líder em soluções empresariais. Entrega de valor em tecnologia e serviço B2B.",
            "Territorios": "Tecnologia, Inovação, Gestão, Alta Performance",
            "TomDeVoz": "Corporativo, inovador, especialista e inspirador. Visionário, colaborativo",
            "PublicoAlvo": "Diretores, gerentes e tomadores de decisão em empresas de médio e grande porte.",
            "RegrasNegativas": "Não usar tom informal demais, evitar jargões vazios, não prometer resultados sem esforço.",
            "RegrasPositivas": "Destaque os diferenciais: - Líder nacional em tecnologia B2B, - +1.300 clientes parceiros, - 97% de retenção."
        }
    ]
    st.session_state['brandbook_df'] = pd.DataFrame(dados_iniciais)

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
        default_headers={"HTTP-Referer": "https://gfo.app", "X-Title": "Gerador GFO"}
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
    if not (wp_url and wp_user and wp_pwd):
        return "Sem credenciais do WordPress configuradas para esta marca. Pule a linkagem interna."
    
    import base64
    wp_pwd_clean = wp_pwd.replace(" ", "").strip()
    credenciais = f"{wp_user}:{wp_pwd_clean}"
    token_auth = base64.b64encode(credenciais.encode('utf-8')).decode('utf-8')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Authorization': f'Basic {token_auth}',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip, deflate, br'
    }

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
        'User-Agent': 'Mozilla/5.0', 
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
                path_data = attrs.get('path') or {}
                link = path_data.get('alias', '') if isinstance(path_data, dict) else ""
                ctx += f"- Título: {titulo}\n  URL: {link}\n"
            return ctx
        return f"Erro Drupal RAG (Status {res.status_code})"
    except Exception as e:
        return f"Erro Drupal RAG: {e}"

@st.cache_data(ttl=300, show_spinner=False)
def listar_posts_wp(wp_url, wp_user, wp_pwd):
    if not (wp_url and wp_user and wp_pwd):
        return []
    
    import base64
    wp_pwd_clean = wp_pwd.replace(" ", "").strip()
    credenciais = f"{wp_user}:{wp_pwd_clean}"
    token_auth = base64.b64encode(credenciais.encode('utf-8')).decode('utf-8')
    
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Authorization': f'Basic {token_auth}',
        'Connection': 'keep-alive'
    }

    separador = "&" if "?" in wp_url else "?"
    search_url = f"{wp_url}{separador}per_page=15&status=publish&_fields=id,title,content,link"
    
    try:
        res = requests.get(search_url, headers=headers, timeout=25)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        pass
    return []

@st.cache_data(ttl=300, show_spinner=False)
def listar_posts_drupal(d_url, d_user, d_pwd):
    if not (d_url and d_user and d_pwd): return []
    import base64
    token_auth = base64.b64encode(f"{d_user}:{d_pwd.replace(' ', '').strip()}".encode('utf-8')).decode('utf-8')
    headers = {
        'User-Agent': 'Mozilla/5.0', 
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
                body_data = attrs.get("body") or {}
                conteudo = body_data.get("value", "") if isinstance(body_data, dict) else ""
                lista_formatada.append({
                    "id": p.get("id"),
                    "title": {"rendered": titulo},
                    "content": {"rendered": conteudo}
                })
            return lista_formatada
    except Exception as e:
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
    5. PRESERVAÇÃO DE DADOS: Mantenha as informações e ideias do texto original. Não invente "Estudos" ou dados matemáticos se eles não estiverem no texto original.
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
    citation = extrair_numero(citation_score) * 20  
    original = extrair_numero(originalidade)
    cita_llm = extrair_numero(citabilidade)
    
    try:
        entity_dict = json.loads(entity_coverage_str)
        entity = int(entity_dict.get("entity_coverage_score", 0))
    except:
        entity = extrair_numero(entity_coverage_str)

    geo = (0.35 * citation) + (0.25 * cita_llm) + (0.25 * entity) + (0.15 * original)

    return {
        "citation_score_normalizado": f"{citation}/100",
        "citabilidade_llm": cita_llm,
        "originalidade": original,
        "entity_coverage": entity,
        "geo_score_final": round(geo, 2),
        "veredito": "Score calculado matematicamente via heurística RAG com pesos fixos."
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
    score = min(len(novas) / 8, 100)
    return {"information_gain_score": round(score, 2), "palavras_unicas_trazidas": len(novas)}

def refinar_artigo_html(html_atual, instrucoes):
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
def executar_geracao_completa(palavra_chave, marca_alvo, publico_alvo, conteudo_adicional="", conteudo_proprietario="", modo_humanizado=False):
    df = st.session_state['brandbook_df']
    marca_info = df[df['Marca'] == marca_alvo].iloc[0].to_dict()
    url_marca = marca_info.get('URL', '')
    from datetime import datetime
    ano_atual = datetime.now().year

    cms_url, cms_user, cms_pwd, cms_type = obter_credenciais_cms(marca_alvo)

    st.write(f"🕵️‍♂️ Fase 0: Buscando Google (Serper + Jina), IAs e RAG Reverso ({cms_type.upper()})...")
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futuro_google = executor.submit(buscar_contexto_google, palavra_chave)
        futuro_ia = executor.submit(buscar_baseline_llm, palavra_chave)
        futuro_reverse = executor.submit(gerar_reverse_queries, palavra_chave)
        
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
6) GATILHOS DE VETO E ANTI-ALUCINAÇÃO (TOLERÂNCIA ZERO):
- REGRA DO DADO ÓRFÃO: É TERMINANTEMENTE PROIBIDO criar briefings sugerindo estatísticas exatas (ex: "37% de aumento", "9 em cada 10") a menos que você tenha a URL profunda e exata fornecida no contexto orgânico. Se não tiver a URL de pesquisa empírica, force o redator a focar em "Argumentação Lógica e Qualitativa" e proíba o uso de números absolutos ou percentuais.
- BLINDAGEM E LINK DE MARCA: Oriente o redator a usar a Marca Alvo exatamente como fornecida e a criar um link (href) para a URL Oficial da marca toda vez que ela for mencionada no texto.

ENTREGÁVEIS DO BRIEFING:
A) ÂNGULO NARRATIVO ÚNICO: escolha 1 (ex.: Quebra de Mito; Guia Tático; Análise de Tendência; Framework Operacional). Justifique em 2-3 linhas focado NAS DORES do público-alvo informado.
B) ESTRUTURA ANTI-FÓRMULA (H2): proponha 4 H2 provocativos, específicos e complementares (sem “O que é”, “Benefícios”, “Conclusão”).
C) MAPA DE EVIDÊNCIAS E DEEP LINKS: Você deve vasculhar o contexto orgânico fornecido para resgatar 2 a 3 DEEP LINKS REAIS. REGRA CRÍTICA: É ESTRITAMENTE PROIBIDO usar links de empresas concorrentes do nicho. Escolha APENAS links de autoridades neutras (Portais de Notícias confiáveis, revistas científicas, órgãos oficiais). Se não houver links neutros, não sugira nenhum.
E) ENTITY AUTHORITY GRAPH: Liste pelo menos 6 entidades institucionais relevantes para o tema para reforçar autoridade semântica.
F) GATILHO DE MARCA (SEM ALUCINAÇÃO): descreva como a marca aparecerá no terço final como um “Estudo de Caso Prático”. FOQUE APENAS na solução específica. É EXPRESSAMENTE PROIBIDO inventar números de clientes, inventar taxas de conversão ou cenários fictícios de antes/depois.
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
Você é um Especialista em SEO Semântico (GEO) e um profissional do setor com vasta experiência prática. 
Sua missão é traduzir o Tom de Voz corporativo em um texto que não pareça um artigo de blog encomendado, mas sim um relato ou análise de quem vive a realidade diariamente.

1. A VOZ DA TRINCHEIRA (EXPERIÊNCIA REAL):
- Escreva como alguém que já participou de reuniões tensas com diretores, ouviu reclamações de clientes e acompanhou dinâmicas reais da operação. 
- Evite a empatia genérica e enlatada de IA (Ex: NUNCA use "Sabemos que o mercado é um desafio..."). Vá direto para o problema real.
- IMPERFEIÇÃO HUMANA CONTROLADA: A cadência deve parecer orgânica. Não tente fechar todos os parágrafos com uma conclusão perfeita ou "redonda". Use transições secas. Textos humanos reais têm cortes e vão direto ao ponto.

2. O DETECTOR DE ROBÔS E CLICHÊS (BLACKLIST ABSOLUTA):
- VETO A FRASES DE IMPACTO GENÉRICAS: Se usar uma frase curta, ela deve trazer INFORMAÇÃO, não drama. Estão TERMINANTEMENTE PROIBIDAS as frases: "Os números não mentem", "Esta é uma falsa dicotomia", "O segredo está em", "Estamos diante de".
- VETO DE VOCABULÁRIO "IA": Jamais use: "no cenário atual", "cada vez mais", "divisor de águas", "é inegável que", "neste artigo veremos", "em resumo", "por fim", "transcendeu".

3. ANCORAGEM NO MUNDO REAL (CRÍTICO PARA INDETECTABILIDADE):
- MEMÓRIA OPERACIONAL: Sempre que explicar um conceito teórico, obrigatoriamente "encoste a ideia na realidade" com uma micro-cena plausível (Ex: uma decisão financeira no meio do mês, o momento da negociação).
- DETALHE IMPERFEITO: Inclua pequenos detalhes contextuais em suas explicações que não são essenciais para o argumento central, mas gritam "fator humano" (ex: "quando o sistema trava").
- FRICÇÃO ANALÍTICA: O texto não pode ser um mar de positividade. Em pelo menos um H2, questione uma prática comum do mercado, aponte um efeito colateral inesperado ou discorde do senso comum. Mostre atrito intelectual.

4. ESTRUTURA GEO INVISÍVEL E SEO:
- CONCEITO FLUIDO: Logo no início, entregue o conceito da palavra-chave em um parágrafo normal, sem usar etiquetas como "Definição:".
- RESPOSTA RÁPIDA: Crie um <h2>Resposta rápida para: [palavra-chave]</h2>. Abaixo dele, responda a dúvida principal em 2 ou 3 linhas narrativas e diretas.
- SÍNTESE VISUAL: Insira a tag exata `<br>Resumo Estratégico<br>` e crie um <ul> com 3 a 5 bullet points valiosos. Limite absoluto de 2 listas no artigo todo.
- CITAÇÃO NATURAL: Inclua a visão de um especialista começando o parágrafo de forma orgânica, como: <p><strong>A visão dos especialistas:</strong> ...</p>

5. REGRAS DE LINKAGEM E BLINDAGEM E-E-A-T (TOLERÂNCIA ZERO):
- VETO TOTAL A RIVAIS: É ESTRITAMENTE PROIBIDO citar o nome ou link de QUALQUER empresa privada ou concorrente. A única marca privada permitida é a [Marca Alvo].
- LINK DA MARCA: Sempre que citar a [Marca Alvo], transforme-a num link HTML OBRIGATÓRIO: <a href="[URL_DA_MARCA]" target="_blank">[NOME_DA_MARCA]</a>.
- RASTREABILIDADE (DEEP LINKS): Use os links externos fornecidos no briefing (Órgãos, Portais de Notícias). Ancore-os naturalmente. Se não tiver a URL real fornecida no briefing para um dado/pesquisa, NÃO cite a instituição ou os números. Evite alucinação de fontes.
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
1.2) Fale DIRETAMENTE com o Público-Alvo definido. Entenda a realidade deles (ex: um gestor busca eficiência).
1.3) Ritmo, profundidade e elegância. Voz ativa. Evite enchimento.
2) PROIBIDO usar jargões de IA como: "No cenário atual", "Cada vez mais", "É inegável que", "É importante ressaltar", "Neste artigo veremos", "Em resumo", "Por fim". 
2.1) VETO DE VOCABULÁRIO IA APRIMORADO (BLACKLIST ABSOLUTA): Estão permanentemente banidas do seu vocabulário as seguintes expressões e suas variações: "cenário em transformação", "transcendeu o status", "mundo globalizado", "mundo contemporâneo", "não é apenas X, mas também Y", "mergulhar em", "verdadeiro divisor de águas", "é fundamental notar", "revolucionar".
2.2) ESTILO JORNALÍSTICO (SHOW, DON'T TELL): Não diga que algo é "inovador" ou "fundamental". Apresente o fato técnico e deixe o leitor concluir isso. Escreva como um analista focado em negócios B2B.
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
11) REGRA DE CAPITALIZAÇÃO (SENTENCE CASE): É ESTRITAMENTE PROIBIDO usar "Title Case" nos títulos H1, H2 e H3. Use o padrão gramatical brasileiro: APENAS a primeira letra da frase e nomes próprios/marcas devem ser maiúsculos.
12) PROIBIDO PARÁGRAFOS SIMÉTRICOS: Verifique o texto antes de entregar. Se você notar que os parágrafos estão visualmente do mesmo tamanho, fragmente-os imediatamente. Obrigatoriamente inclua frases isoladas para criar respiros visuais profundos.
13) VARIAÇÃO HUMANA DE RITMO (OBRIGATÓRIO E EXTREMO):
Humanos não escrevem com ritmo perfeitamente regular. Introduza variação natural drástica.
14) LISTAS COM CONTEXTO E LIMITE: O texto não pode parecer uma apresentação de slides. Se usar uma lista, é obrigatório introduzi-la com contexto e concluí-la com forte interpretação analítica.

REGRAS DE LINKAGEM, FONTES E VETOS (E-E-A-T):
15) VETO TOTAL A RIVAIS: É ESTRITAMENTE PROIBIDO citar o nome ou inserir hiperlinks para QUALQUER outra empresa concorrente. A única marca privada do setor que pode ser citada é a Marca Alvo.
16) PROTOCOLO DE RASTREABILIDADE (DEEP LINKS OBRIGATÓRIOS): É OBRIGATÓRIO incluir pelo menos 2 a 3 links externos (<a href="..." target="_blank">) ancorando afirmações ou dados. 
17) VETO AO LAZY LINKING: É ESTRITAMENTE PROIBIDO linkar para homepages genéricas. Todo link DEVE ser um DEEP LINK.
18) FONTES NEUTRAS E DEEP LINKING: Todo link externo deve ir para páginas específicas, nunca homepages genéricas. Os links externos DEVEM ser exclusivamente de órgãos oficiais, institutos de pesquisa ou portais de notícias sérios.
19) FONTE DOS LINKS (PROIBIDO ALUCINAR URL): Use EXCLUSIVAMENTE os deep links que foram explicitamente fornecidos no briefing. É ESTRITAMENTE PROIBIDO inventar, adivinhar ou construir URLs da sua própria memória. Se o briefing não te fornecer uma URL válida e real, você está liberado da obrigação de colocar links externos.
20) REGRA DE OURO DOS DADOS CITADOS (ANTI-PENALIZAÇÃO): É ESTRITAMENTE PROIBIDO citar o nome de associações, institutos, pesquisas ou dados numéricos de mercado sem ancorar a citação em um link (<a href="...">). Se você não tiver o link externo real para inserir, NÃO CITE o nome da instituição ou o dado; reescreva a frase de forma puramente conceitual. Exceção: Dados institucionais da própria Marca Alvo não precisam de link.
21) LINKAGEM INTERNA (OBRIGAÇÃO ABSOLUTA): Você receberá uma lista chamada "ARTIGOS INTERNOS DISPONÍVEIS". É UMA EXIGÊNCIA INEGOCIÁVEL que você escolha de 1 a 2 artigos dessa lista e crie links HTML (<a href="[URL]">) no meio do seu texto.

ESTRATÉGIA EDITORIAL, NARRATIVA E VOZ:
22) DIRECIONAMENTO ESTRATÉGICO DO ESPECIALISTA (BÚSSOLA DO ARTIGO): O usuário pode fornecer um bloco de "Conteúdo Adicional". Você não precisa fazer um "copia e cola" literal e engessado, mas DEVE usar esses elementos como a base principal da sua argumentação.
23) FRAMEWORK DO ESTUDO DE CASO (P.A.R.): O seu "Estudo de Caso" não pode parecer um panfleto publicitário. Ele deve ser escrito na estrutura Problema > Ação da Marca > Resultado.
24) ENTITY SATURATION: Integre naturalmente as entidades mapeadas para provar domínio do nicho.
25) VOZ EDITORIAL DE ANALISTA: Escreva como um analista corporativo que observa padrões do setor.
26) OBSERVAÇÃO OPERACIONAL (ANTI-TEXTO GENÉRICO): Sempre que explicar um conceito, inclua uma observação concreta da situação ou implementação.
27) CONTRAPONTO ANALÍTICO (OBRIGATÓRIO EM PELO MENOS 1 H2): Inclua pelo menos um momento do texto onde uma crença comum do setor é questionada ou refinada.
28) MICRO-ANÁLISE CAUSAL: Sempre que apresentar um benefício ou prática, explique rapidamente o mecanismo por trás.
"""

    user_2 = f"""
Palavra-chave ou Consulta: '{palavra_chave}'

CONTEXTO TEMPORAL: Ano de {ano_atual}. Não projete o futuro sem evidência.
    
CONTEÚDO ADICIONAL DO ESPECIALISTA (DIRECIONAMENTO HUMANO OBRIGATÓRIO):
{conteudo_adicional if conteudo_adicional else "Nenhum conteúdo extra fornecido. Siga apenas o briefing."}

CONTEÚDO PROPRIETÁRIO INEGOCIÁVEL (COPIAR E COLAR EXATAMENTE COMO ESTÁ):
{conteudo_proprietario if conteudo_proprietario else "Nenhum conteúdo proprietário exigido."}

O QUE A CONCORRÊNCIA DIZ HOJE:
{contexto_google}

SEU BRIEFING (siga à risca o ângulo e integre o Entity Authority Graph):
{analise}

DIRECIONAMENTO DE COPYWRITING E MARCA:
- Público-Alvo Deste Texto: {publico_alvo}
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
5. VETO A RIVAIS: Verifique seu texto e as URLs dos seus links (<a href="...>). Você citou o nome ou o site de ALGUMA OUTRA EMPRESA CONCORRENTE que não seja a {marca_alvo}? SE SIM, remova imediatamente.
6. O seu "Estudo de Caso" foca na tecnologia/metodologia real da {marca_alvo}? Verifique se você inventou historinha de cliente fictício ou números falsos. Se sim, APAGUE ISSO.
7. CHECK DE DEEP LINKS: Você incluiu pelo menos 2 links externos? Olhe para as URLs dentro do <a href>. Elas são DEEP LINKS reais?
8. Você garantiu que TODAS as menções à {marca_alvo} contêm o link <a href="{url_marca}">?
9. Você checou a existência de dados numéricos no briefing? Se não houver, garanta que sua abordagem é conceitual e livre de alucinações matemáticas.
10. AUDITORIA DE FONTES (TOLERÂNCIA ZERO): Você citou alguma Associação, Instituto, Estudo, Pesquisa, Ministério no texto? Se sim, a tag de link (<a href="...">) está EXATAMENTE junto ao nome deles? Se estiver sem link, APAGUE a frase inteira imediatamente.
</checklist_de_seguranca_obrigatorio>

Escreva o ARTIGO FINAL em HTML conforme as regras GEO, preservando exatamente os marcadores:
<br>Resumo Estratégico<br>
<br>Perguntas Frequentes<br>

ATENÇÃO: Pare de escrever IMEDIATAMENTE após a última tag HTML. NUNCA gere auto-avaliações, comentários ou textos que comecem com "AI:".
"""
    artigo_html = chamar_llm(system_2, user_2, model="anthropic/claude-3.7-sonnet", temperature=0.45)
    artigo_html = re.sub(r'^```html\n|```$', '', artigo_html, flags=re.MULTILINE).strip()
    
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
4) 'dicas_imagens': exatamente 2 strings em inglês, MUITO CURTAS E SIMPLES (máximo 1 a 2 palavras). É ESTRITAMENTE PROIBIDO gerar frases longas.
5) 'schema_faq': JSON-LD **FAQPage** com @context "[https://schema.org](https://schema.org)", @type "FAQPage" e mainEntity. Extraídas textualmente do HTML fornecido. Se não houver, {{}}.
"""

    user_3 = f"HTML COMPLETO:\n{artigo_html}"

    dicas_json = chamar_llm(system_3, user_3, model="anthropic/claude-3.7-sonnet", temperature=0.1, response_format={"type": "json_object"})

    try:
        json_limpo = dicas_json.strip().removeprefix('```json').removesuffix('```').strip()
        meta_dicas = json.loads(json_limpo)
        termos_busca = meta_dicas.get('dicas_imagens', [])
        UNSPLASH_KEY = st.secrets.get("UNSPLASH_KEY", "")
        
        if isinstance(termos_busca, list):
            for i, termo in enumerate(termos_busca[:2]):
                img_html_pronta = ""
                if UNSPLASH_KEY:
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
                    clean_termo = str(termo).replace("'", "").replace('"', '').strip()
                    p_codificado = urllib.parse.quote(clean_termo)
                    base_poll = "https://image.pollinations.ai/prompt/"
                    img_html_pronta = f'<img src="{base_poll}{p_codificado}?width=1024&height=512&nologo=true&model=flux" alt="{clean_termo}" style="width:100%; border-radius:8px;" loading="lazy" decoding="async" />'
                    
                if img_html_pronta:
                    alvo_replace = '<br>Resumo Estratégico<br>' if i == 0 else '<br>Perguntas Frequentes<br>'
                    artigo_html = artigo_html.replace(alvo_replace, f'{img_html_pronta}\n{alvo_replace}', 1)
    except Exception as e:
        st.error(f"Erro ao injetar imagem: {e}")

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
    
    headers = {
        'User-Agent': 'Mozilla/5.0',
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
    node_type = "node--" + d_url.rstrip('/').split('/')[-1] 
    
    payload = {
        "data": {
            "type": node_type,
            "attributes": {
                "title": titulo,
                "body": {"value": conteudo_html, "format": "full_html"},
                "status": False
            }
        }
    }
    
    token_auth = base64.b64encode(f"{d_user}:{d_pwd.replace(' ', '').strip()}".encode('utf-8')).decode('utf-8')
    headers = {
        'User-Agent': 'Mozilla/5.0', 
        'Accept': 'application/vnd.api+json', 
        'Content-Type': 'application/vnd.api+json', 
        'Authorization': f'Basic {token_auth}'
    }
    try:
        return requests.post(d_url, json=payload, headers=headers, timeout=30)
    except Exception as e:
        class ErrorRes: 
            status_code = 500
            text = f"Erro interno de conexão: {str(e)}"
            def json(self): return {}
        return ErrorRes()

import PyPDF2
def extrair_texto_pdf(arquivo_pdf):
    try:
        leitor = PyPDF2.PdfReader(arquivo_pdf)
        texto_completo = ""
        for pagina in leitor.pages:
            texto_extrato = pagina.extract_text()
            if texto_extrato:
                texto_completo += texto_extrato + "\n"
        return texto_completo
    except Exception as e:
        return f"Erro ao ler PDF: {e}"

def executar_adaptacao_pdf(palavra_chave, publico, marca, texto_base_pdf):
    df = st.session_state['brandbook_df']
    marca_info = df[df['Marca'] == marca].iloc[0].to_dict()
    url_marca = marca_info.get('URL', '')

    system = """Você é um Copywriter Especialista em Inbound Marketing, GEO e Repurposing de Conteúdo.
    Sua missão é ler o texto bruto de um E-book/Guia em PDF e transformá-lo em um "Artigo Resumo / Teaser" em HTML. 
    O objetivo deste artigo NÃO é entregar todo o conteúdo, mas sim gerar curiosidade e atuar como uma página de atração para que o leitor baixe o material completo.
    
    REGRAS INVIOLÁVEIS DE COPYWRITING E CONVERSÃO:
    1. FONTE DA VERDADE (ANTI-ALUCINAÇÃO): Use EXCLUSIVAMENTE os dados e exemplos presentes no texto do PDF fornecido. Não invente nada fora dele.
    2. DIFERENCIAÇÃO EXTREMA DE MARCA (CRÍTICO): O seu texto, o seu TÍTULO (H1) e a sua escolha de "Spoiler" DEVEM ser guiados 100% pelo Posicionamento e Territórios da Marca Alvo. É ESTRITAMENTE PROIBIDO gerar um título ou ângulo genérico. 
       -> Se a marca foca em "Inovação", o ângulo do artigo deve ser a transformação tecnológica e modernização.
    3. BRAND WEAVING (INSERÇÃO NATURAL DA MARCA): Não deixe para citar a marca apenas no final! Integre o nome da marca e seus diferenciais no MEIO do texto.
    4. BLACKLIST DE EXAGEROS (TOLERÂNCIA ZERO): É estritamente proibido usar termos hiperbólicos, sensacionalistas ou jargões vazios de IA. NUNCA use palavras como: "radicalmente", "revolucionário", "divisor de águas".
    5. ESTRUTURA TEASER (A TÉCNICA DO SPOILER): É expressamente PROIBIDO resumir todos os tópicos ou listar todas as perguntas/respostas do PDF. Faça uma introdução sobre o cenário e escolha APENAS UM conceito forte. Apele para a curiosidade sobre o que ficou de fora.
    6. O GATILHO PARA O DOWNLOAD (TOM CONVIDATIVO): No final do texto, crie a transição para o download de forma amigável.
    
    REGRAS DE GEO E HTML:
    8. ASSIMETRIA VISUAL: Quebre blocos de texto maciços. Intercale parágrafos de 3-4 linhas com parágrafos de uma única frase de impacto.
    9. ESTRUTURA DE TÍTULOS E ANSWER-FIRST SUAVIZADO: O texto DEVE começar obrigatoriamente com uma tag <h1> contendo o título chamativo. Logo abaixo, crie um <h2>Resposta rápida para: [palavra-chave]</h2>.
    10. PREVENÇÃO DE ERRO JSON (CRÍTICO): Seu retorno será processado por um json.loads(). É OBRIGATÓRIO usar aspas simples (') nas tags HTML (ex: <a href='link'>). 
    
    RETORNE EXCLUSIVAMENTE UM JSON:
    {
        "diagnostico": "Explique qual spoiler você escolheu.",
        "melhorias_aplicadas": ["Diferenciação de Ângulo", "Brand Weaving", "Técnica do Spoiler", "Sem Exageros"],
        "html_novo": "O código HTML completo usando aspas simples e escapando aspas duplas internas"
    }
    """
    
    user = f"""
    PALAVRA-CHAVE FOCO: '{palavra_chave}'
    PÚBLICO-ALVO: {publico}
    MARCA ALVO: {marca}
    URL DA MARCA OBRIGATÓRIA: {url_marca}
    
    DIRETRIZES DA MARCA ({marca}):
    - Posicionamento: {marca_info['Posicionamento']}
    - Territórios Estratégicos: {marca_info.get('Territorios', 'Geral')}
    - Tom de Voz Exigido: {marca_info['TomDeVoz']}
    - Regras Positivas: {marca_info.get('RegrasPositivas', '')}
    - Proibido (Regras Negativas): {marca_info['RegrasNegativas']}
    
    TEXTO BRUTO EXTRAÍDO DO PDF (E-BOOK/GUIA) PARA SER TRANSFORMADO EM TEASER:
    {texto_base_pdf}
    """
    
    return chamar_llm(system, user, model="anthropic/claude-3.7-sonnet", temperature=0.4, response_format={"type": "json_object"})
    
# ==========================================
# 5. INTERFACE PRINCIPAL
# ==========================================

if st.session_state['current_page'] == "BrandBook":
    st.markdown("### 🏢 Edite as regras, marcas e diretrizes:")
    st.session_state['brandbook_df'] = st.data_editor(st.session_state['brandbook_df'], num_rows="dynamic", width="stretch")
    st.info("💡 Dica: Adicione regras específicas na coluna 'RegrasPositivas' para cada marca que quiser adicionar.")

elif st.session_state['current_page'] == "Gerador de Artigos":
    gerar_btn = False 
    
    if not st.session_state['show_inputs']:
        # ==========================================
        # HERO SECTION E CARDS DE VENDA
        # ==========================================
        st.markdown("""
        <style>
        .animated-ia::after {
            content: 'Gemini';
            animation: switchWord 6s infinite;
            color: #4ED1A3;
            font-weight: 700;
        }
        @keyframes switchWord {
            0%, 20%  { content: 'Gemini'; }
            25%, 45% { content: 'Perplexity'; }
            50%, 70% { content: 'Chat GPT'; }
            75%, 95% { content: 'Copilot'; }
            100%     { content: 'Gemini'; }
        }
        </style>
        
        <div style="text-align: center; margin-top: -3.5rem; margin-bottom: 1rem;">
            <div class="gfo-tag" style="margin-bottom: 0.5rem;">GEO MACHINE AGENT</div>
            <h1 style="font-size: 3rem; margin-top: 0rem; margin-bottom: 0.5rem;">Machine GEO <span style="color: #4ED1A3;">Generative Focos Only</span></h1>
            <p style="font-size: 1.1rem; color: #4B5563; margin-top: 0; font-family: 'Inter', sans-serif;">
                This agente is about creat texts for LLMs : <span class="animated-ia"></span>
            </p>
        </div>
        """, unsafe_allow_html=True)

        col_cta1, col_cta2, col_cta3 = st.columns([1, 1, 1])
        with col_cta2:
            if st.button("Gerar artigo 🚀", type="primary", use_container_width=True):
                st.session_state['show_inputs'] = True
                st.rerun()
        
        st.markdown(pipeline_html, unsafe_allow_html=True)

        st.markdown("""
        <style>
        @keyframes bounce-down {
            0%, 100% { transform: translateY(0); opacity: 0.4; }
            50% { transform: translateY(10px); opacity: 1; }
        }
        .scroll-indicator {
            text-align: center;
            margin-top: 30px;
            margin-bottom: -10px;
            color: #9CA3AF;
            animation: bounce-down 2s infinite ease-in-out;
        }
        </style>
        <div class="scroll-indicator">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
            <div style="font-size: 12px; margin-top: 2px; font-family: 'Inter', sans-serif; font-weight: 500; letter-spacing: 0.05em; text-transform: uppercase;">VEJA MAIS</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<h3 style='margin-top: 3rem; font-size: 1.5rem;'>As novidades. Veja o que acabou de chegar.</h3>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown("""
            <div class="saas-card">
                <img src="https://upload.wikimedia.org/wikipedia/commons/0/04/ChatGPT_logo.svg" alt="GPT-4o Logo" style="height: 32px; margin-bottom: 16px;">
                <div class="card-title">Estrategista (GPT-4o)</div>
                <div class="card-text">Analisa a concorrência e cria o briefing estrutural com alto Information Gain e regras E-E-A-T.</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown("""
            <div class="saas-card">
                <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Claude_AI_symbol.svg" alt="Claude 3.7 Logo" style="height: 32px; margin-bottom: 16px;">
                <div class="card-title">Redator (Claude 3.7)</div>
                <div class="card-text">A inteligência mais avançada para Copywriting. Escreve com fluidez humana e variação rítmica.</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown("""
            <div class="saas-card">
                <div style="font-size: 2rem; margin-bottom: 8px;">🌐</div>
                <div class="card-title">AI Search Native</div>
                <div class="card-text">Realiza uma varredura profunda na web em tempo real, extraindo o conteúdo para mapear o 'Entity Gap' exato do seu nicho.</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown("""
            <div class="saas-card">
                <div style="font-size: 2rem; margin-bottom: 8px;">🔗</div>
                <div class="card-title">RAG Reverso (CMS)</div>
                <div class="card-text">Conecta-se ao seu CMS e faz a linkagem interna automática com os artigos que você já publicou.</div>
            </div>
            """, unsafe_allow_html=True)

    else:
        # ==========================================
        # FORMULÁRIO DE GERAÇÃO
        # ==========================================
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="font-size: 2rem;">Machine GEO <span style="color: #4ED1A3; font-size: 1.2rem;">Generative Focos Only</span></h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(pipeline_html, unsafe_allow_html=True)

        caixa_topo = st.container()
        st.markdown("<br>", unsafe_allow_html=True) 
        
        col1, col2 = st.columns([1, 2])
        with col1:
            marca_selecionada = st.selectbox("Selecione a Marca", st.session_state['brandbook_df']['Marca'].tolist())
            
            try:
                publicos_da_marca = st.session_state['brandbook_df'][st.session_state['brandbook_df']['Marca'] == marca_selecionada]['PublicoAlvo'].iloc[0]
                opcoes_publico = [p.strip() for p in publicos_da_marca.split('.') if p.strip()]
                if not opcoes_publico: opcoes_publico = ["Público Geral (Baseado na Keyword)"]
                else: opcoes_publico.append("Público Geral (Baseado na Keyword)")
            except Exception:
                opcoes_publico = ["Público Geral (Baseado na Keyword)"]
                
            opcoes_publico.append("✍️ Digitar outro público (Personalizado)...")
            escolha_publico = st.selectbox("🎯 Para quem estamos escrevendo?", opcoes_publico)
            
            if escolha_publico == "✍️ Digitar outro público (Personalizado)...":
                publico_selecionado = st.text_input("Qual é o público-alvo?", placeholder="Ex: diretores, gestores, desenvolvedores...")
            else:
                publico_selecionado = escolha_publico

            palavra_chave_input = st.text_area(
                "🔑 Palavra-chave ou Consulta/Query de Pesquisa", 
                placeholder="Ex: melhores práticas de gestão de equipe remota"
            )
            
            conteudo_adicional_input = st.text_area(
                "📚 Conteúdo Adicional (Opcional)", 
                height=120,
                placeholder="Exemplos do que inserir aqui:\n- Links de referência: https://site.com/pesquisa-recente\n- Teorias: Cite a metodologia ágil sobre o assunto.\n- Insumos: 'Nosso cliente aumentou os lucros em 20%...'"
            )
            
            conteudo_proprietario_input = st.text_area(
                "🔒 Conteúdo Proprietário Inegociável (Opcional)", 
                height=100,
                help="Frases exatas, citações ou parágrafos que a IA é OBRIGADA a incluir literalmente no texto gerado sem alterar nenhuma palavra.",
                placeholder="Ex: 'Segundo nosso CEO, a inovação transforma o amanhã.' (A IA vai colar este texto exato dentro do artigo)."
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            modo_humanizado = st.toggle("✨ Ativar Escrita Empática / Mentoria (Beta)", value=False, help="Se ativado, a IA usa um prompt focado em fluidez humana e cadência vocal.")
            st.markdown("<br>", unsafe_allow_html=True)
    
            gerar_btn = st.button("🚀 Gerar Artigo em HTML", width="stretch", type="primary")
        
            st.markdown("---")
            
            cms_u, cms_usr, cms_p, cms_t = obter_credenciais_cms(marca_selecionada)
            WP_READY = bool(cms_u and cms_usr and cms_p)
    
            if not WP_READY:
                st.warning(f"🔌 Integração CMS inativa para a marca {marca_selecionada}. Faltam as credenciais.")
            else:
                with st.spinner(f"Verificando conexão com o Firewall do {cms_t.upper()}..."):
                    try:
                        import base64
                        token_teste = base64.b64encode(f"{cms_usr}:{cms_p.replace(' ', '').strip()}".encode('utf-8')).decode('utf-8')
                        user_agent_ping = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        
                        headers_teste = {
                            'User-Agent': user_agent_ping, 
                            'Accept': 'application/json' if cms_t == 'wp' else 'application/vnd.api+json',
                            'Authorization': f'Basic {token_teste}',
                            'Connection': 'keep-alive'
                        }
                        
                        url_ping = f"{cms_u}?per_page=1" if cms_t == "wp" else f"{cms_u}?page[limit]=1"
                        res_ping = requests.get(url_ping, headers=headers_teste, timeout=5)
                        
                        if res_ping.status_code == 200:
                            st.success(f"🔌 Conectado e Autorizado no {cms_t.upper()} da marca: {marca_selecionada}")
                        elif res_ping.status_code in [403, 401]:
                            st.error(f"🛑 Credenciais OK, mas o Firewall (WAF) bloqueou a leitura da marca {marca_selecionada} (Erro {res_ping.status_code}). Solicite whitelist do User-Agent para a TI.")
                            WP_READY = False 
                        else:
                            st.warning(f"⚠️ API respondeu com Erro {res_ping.status_code}. O RAG Reverso pode falhar.")
                    except Exception:
                        st.error(f"🔌 O domínio da marca {marca_selecionada} não respondeu a tempo (Timeout).")
                        WP_READY = False

    if gerar_btn:
        if not TOKEN:
            st.error("⚠️ Erro: A chave OPENROUTER_KEY não foi encontrada nos Secrets.")
        elif not palavra_chave_input:
            st.warning("⚠️ Por favor, digite uma palavra-chave.")
        else:
            with col2:
                with st.status("🤖 Processando Machine GEO...", expanded=True) as status:
                    try:
                        (
                            artigo_html, dicas_json, google_data, ia_data, entity_gap, 
                            score_originalidade, citabilidade, cluster, reverse_queries, 
                            citation_score, entity_coverage, geo_score, retrieval_simulation, 
                            hijacking_risk, ai_simulation, chunk_citability, answer_first, 
                            rag_chunks, evidence_density, information_gain, contexto_wp
                        ) = executar_geracao_completa(
                            palavra_chave_input, marca_selecionada, publico_selecionado, 
                            conteudo_adicional_input, conteudo_proprietario_input, modo_humanizado
                        )
                        
                        st.session_state['art_gerado'] = artigo_html
                        st.session_state['metas_geradas'] = dicas_json
                        st.session_state['google_ctx'] = google_data
                        st.session_state['ia_ctx'] = ia_data
                        st.session_state['entity_gap'] = entity_gap
                        st.session_state['score_originalidade'] = score_originalidade
                        st.session_state['citabilidade'] = citabilidade
                        st.session_state['cluster'] = cluster
                        st.session_state['reverse_queries'] = reverse_queries
                        st.session_state['citation_score'] = citation_score
                        st.session_state['entity_coverage'] = entity_coverage
                        st.session_state['geo_score'] = geo_score
                        st.session_state['retrieval_simulation'] = retrieval_simulation
                        st.session_state['hijacking_risk'] = hijacking_risk
                        st.session_state['ai_simulation'] = ai_simulation
                        st.session_state['chunk_citability'] = chunk_citability
                        st.session_state['answer_first'] = answer_first
                        st.session_state['rag_chunks'] = rag_chunks
                        st.session_state['evidence_density'] = evidence_density
                        st.session_state['information_gain'] = information_gain
                        st.session_state['contexto_wp'] = contexto_wp
                        
                        st.session_state['marca_atual'] = marca_selecionada
                        st.session_state['keyword_atual'] = palavra_chave_input
                        status.update(label="✅ Artigo gerado com sucesso!", state="complete", expanded=False)
                    except Exception as e:
                        status.update(label="❌ Erro durante a geração", state="error")
                        st.error(f"Erro Crítico: {e}")

    if 'art_gerado' in st.session_state:
        with col2:
            st.success("✨ Tudo pronto! Seu artigo foi gerado e estruturado com sucesso.")
            
            kpi_c1, kpi_c2 = st.columns(2)
            with kpi_c1:
                st.metric("🎯 Nota Geral de Estrutura (GEO)", st.session_state.get('citation_score', 'N/A'), help="Baseado em 5 critérios que o Google e as IAs mais valorizam hoje.")
            
            try:
                string_json_limpa = st.session_state['metas_geradas'].strip().removeprefix('```json').removesuffix('```').strip()
                meta_validada = MetadadosArtigo.model_validate_json(string_json_limpa)
                meta = meta_validada.model_dump()
                st.subheader(meta.get("title", "Artigo Gerado"))
            except Exception:
                meta = {"title": "Artigo Gerado (JSON Fallback)", "meta_description": "", "dicas_imagens": [], "schema_faq": {}}
                st.subheader("Artigo Gerado")

            st.markdown("<br>", unsafe_allow_html=True)

            tab_html, tab_dash, tab_seo, tab_ia = st.tabs([
                "👁️ Ler e Editar Artigo", 
                "📊 Dashboard Rápido", 
                "🧠 Raio-X Técnico de SEO", 
                "🤖 Como as IAs Enxergam"
            ])

            with tab_html:
                modo_visualizacao = st.radio("O que você deseja fazer?", ["📖 Modo de Leitura", "✏️ Modo de Edição Manual"], horizontal=True, label_visibility="collapsed")
                
                if modo_visualizacao == "📖 Modo de Leitura":
                    
                    componente_copiar = f"""
                    <div style="font-family: 'Inter', sans-serif;">
                        <button id="copy-btn" onclick="copyText()" style="background-color: #111827; color: white; border: none; padding: 12px 20px; border-radius: 8px; width: 100%; cursor: pointer; font-weight: 600; font-size: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); transition: all 0.3s;">
                            📋 Copiar Texto Formatado (Para colar no Docs/Word)
                        </button>
                        <div id="content-to-copy" style="position: absolute; left: -9999px;">
                            {st.session_state['art_gerado']}
                        </div>
                        <script>
                            function copyText() {{
                                var content = document.getElementById("content-to-copy");
                                var range = document.createRange();
                                range.selectNodeContents(content);
                                var selection = window.getSelection();
                                selection.removeAllRanges();
                                selection.addRange(range);
                                try {{
                                    document.execCommand("copy");
                                    var btn = document.getElementById("copy-btn");
                                    btn.innerHTML = "✅ Texto copiado com sucesso! Agora é só dar Ctrl+V no Docs.";
                                    btn.style.backgroundColor = "#4ED1A3"; // Verde GFO
                                    setTimeout(function() {{
                                        btn.innerHTML = "📋 Copiar Texto Formatado (Para colar no Docs/Word)";
                                        btn.style.backgroundColor = "#111827"; // Volta pro Preto
                                    }}, 3000);
                                }} catch (err) {{
                                    console.error("Erro ao copiar: ", err);
                                }}
                                selection.removeAllRanges();
                            }}
                        </script>
                    </div>
                    """
                    st.components.v1.html(componente_copiar, height=65)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### 👁️ Pré-visualização do Blog")
                    
                    html_preview = f"<div style='padding: 20px; border: 1px solid #E5E7EB; border-radius: 8px; background-color: #FFFFFF; color: #111827;'>{st.session_state['art_gerado']}</div>"
                    st.markdown(html_preview, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    with st.expander("📋 Ver Código Fonte (HTML puro)"):
                        st.caption("Passe o mouse no canto superior direito da caixa preta abaixo e clique no ícone para copiar as tags HTML.")
                        st.code(st.session_state['art_gerado'], language="html")

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### 🪄 Comentários para edição com IA")
                    st.caption("Escreva o que você deseja alterar no texto acima. A IA vai modificar apenas o trecho solicitado e manter o resto do artigo intacto.")
                    
                    instrucao_ajuste = st.text_area("Instruções:", placeholder="Ex: Substitua a palavra no segundo parágrafo... ou Remova o último tópico.", label_visibility="collapsed")
                    
                    botao_habilitado = bool(instrucao_ajuste.strip())
                    
                    if st.button("✨ Refinar Texto com IA", type="secondary", disabled=not botao_habilitado, use_container_width=True):
                        with st.spinner("Cirurgia em andamento... A IA está reescrevendo apenas o trecho solicitado..."):
                            try:
                                novo_html = refinar_artigo_html(st.session_state['art_gerado'], instrucao_ajuste)
                                
                                novo_html = re.sub(r'^```html\n|```$', '', novo_html, flags=re.MULTILINE).strip()
                                if '<' in novo_html and '>' in novo_html:
                                    novo_html = novo_html[novo_html.find('<') : novo_html.rfind('>') + 1]
                                
                                st.session_state['art_gerado'] = novo_html
                                st.success("✅ Ajuste aplicado com sucesso!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao tentar refinar o texto: {e}")

                else:
                    st.markdown("### ✏️ Edição Manual de Texto/HTML")
                    st.caption("Faça as alterações que desejar no texto ou nas tags abaixo e clique em Salvar.")
                    
                    html_editado = st.text_area("Edite o conteúdo diretamente abaixo:", value=st.session_state['art_gerado'], height=450, label_visibility="collapsed")
                    
                    if st.button("💾 Salvar Edições Manuais", type="primary"):
                        st.session_state['art_gerado'] = html_editado
                        st.success("✅ Edições salvas com sucesso! Alterne para o 'Modo de Leitura' para ver o resultado.")
                        time.sleep(1.5)
                        st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)
                cms_u, cms_usr, cms_p, cms_t = obter_credenciais_cms(st.session_state['marca_atual'])
                if cms_u and cms_usr and cms_p:
                    st.subheader(f"🌐 Publicação Direta ({cms_t.upper()})")
                    if st.button(f"📤 Enviar Rascunho para {cms_t.upper()} ({st.session_state['marca_atual']})", type="primary", width="stretch", key="btn_pub_principal"):
                        with st.spinner(f"Enviando via API para o {cms_t.upper()}..."):
                            if cms_t == "drupal":
                                res = publicar_drupal(meta.get("title", st.session_state['keyword_atual']), st.session_state['art_gerado'], meta, cms_u, cms_usr, cms_p)
                            else:
                                res = publicar_wp(meta.get("title", st.session_state['keyword_atual']), st.session_state['art_gerado'], meta, cms_u, cms_usr, cms_p)
                            
                            if hasattr(res, 'status_code') and res.status_code in [200, 201]:
                                link_retorno = res.json().get('link') if hasattr(res, 'json') else "Rascunho criado!"
                                st.success(f"✅ Rascunho criado com sucesso! | {link_retorno}")
                            else:
                                erro_status = res.status_code if hasattr(res, 'status_code') else 'Desconhecido'
                                erro_texto = res.text if hasattr(res, 'text') else 'Sem detalhes'
                                st.error(f"❌ Falha ao enviar (Erro HTTP {erro_status}). Resposta do Servidor: {erro_texto}")

            with tab_dash:
                st.info("**O que é esta aba?** Aqui estão as métricas essenciais para garantir que o seu texto será lido por humanos e ranqueado pelo Google.")
                
                with st.expander("🚀 Qualidade Global do Texto (GEO Score)", expanded=True):
                    st.markdown("Uma nota de 0 a 100 que resume se o texto está direto ao ponto, original e bem estruturado. **Acima de 80 é excelente.**")
                    st.json(st.session_state.get('geo_score', '{}'))
                    
                with st.expander("📑 O texto está fácil de ler? (Chunk Citability)", expanded=True):
                    st.markdown("IAs odeiam blocos gigantes de texto. Aqui medimos se o artigo tem **parágrafos curtos, listas e respostas diretas** logo no início (Answer-First).")
                    st.json(st.session_state.get('chunk_citability', '{}'))
                    st.json(st.session_state.get('answer_first', '{}'))

                with st.expander("🥇 O texto traz novidades? (Originalidade e Dados)", expanded=True):
                    st.markdown("O Google pune textos que só 'reciclam' o que já existe. Avaliamos se você trouxe **links de pesquisa, dados reais (Densidade de Evidências)** e palavras novas em relação aos concorrentes.")
                    st.json(st.session_state.get('evidence_density', '{}'))
                    st.json(st.session_state.get('information_gain', '{}'))
                    st.markdown(st.session_state.get('score_originalidade', '⚠️ Sem dados.'))

            with tab_seo:
                st.info("**O que é esta aba?** Voltada para quem entende de SEO. Mostra se usamos o vocabulário certo e como amarrar este artigo com outros no seu blog.")
                
                with st.expander("🧩 Uso de Jargões do Nicho (Entity Coverage)", expanded=True):
                    st.markdown("Avaliamos se o texto contém as 'Entidades' (termos técnicos e jargões) que provam para o Google que você é especialista no assunto, cobrindo buracos que os concorrentes deixaram (Entity Gap).")
                    st.json(st.session_state.get('entity_coverage', '{}'))
                    st.markdown(st.session_state.get('entity_gap', '⚠️ Sem dados.'))

                with st.expander("🗺️ Pautas Futuras (Content Cluster)", expanded=False):
                    st.markdown("Ideias de novos artigos que você pode escrever para linkar com este, criando uma 'Teia de Autoridade' no seu blog.")
                    st.markdown(st.session_state.get('cluster', '⚠️ Sem dados.'))
                    
                with st.expander("🔗 Linkagem Interna Automática", expanded=False):
                    st.markdown("O Motor vasculhou seu CMS e obrigou a IA a linkar este artigo novo com posts antigos da sua marca para fortalecer seu SEO.")
                    st.markdown(st.session_state.get('contexto_wp', '⚠️ Sem dados.'))

            with tab_ia:
                st.info("**O que é esta aba?** Descubra se o ChatGPT ou o Perplexity usariam o seu texto como fonte oficial para responder a um usuário.")
                
                with st.expander("🔎 Chance de virar Fonte Oficial (Retrieval Simulation)", expanded=True):
                    st.markdown("A nossa simulação testa se o seu texto é neutro e confiável o suficiente para ser citado com link por uma Inteligência Artificial.")
                    st.json(st.session_state.get('retrieval_simulation', '{}'))
                    st.markdown(st.session_state.get('citabilidade', '⚠️ Sem dados.'))
                    
                with st.expander("⚠️ Risco de perder o leitor (Hijacking)", expanded=False):
                    st.markdown("Se o seu texto enrolar muito para explicar um conceito, uma IA concorrente pode 'roubar' sua citação simplesmente por ser mais didática. Avaliamos esse risco aqui.")
                    st.json(st.session_state.get('hijacking_risk', '{}'))
                    
                with st.expander("🤖 Teste Real: Como a resposta apareceria no ChatGPT", expanded=False):
                    st.markdown("Simulamos a tela do usuário final. Se ele perguntasse sobre esse tema para uma IA, é assim que a resposta seria gerada usando apenas o seu artigo como base.")
                    st.json(st.session_state.get('ai_simulation', '{}'))
                    
                with st.expander("🔄 O que as pessoas realmente perguntam? (Search Intent)", expanded=False):
                    st.markdown("Engenharia reversa: mapeamos as perguntas exatas que usuários leigos digitam no Google e as dúvidas profundas que a IA tenta resolver.")
                    st.json(st.session_state.get('reverse_queries', '{}'))
                            
# ==========================================
# 6. MONITOR DE GEO (GAMIFICAÇÃO E AUDITORIA)
# ==========================================
elif st.session_state['current_page'] == "Monitor de GEO":
    st.subheader("🔍 Monitor de Autoridade GEO")
    st.caption("Esta aba utiliza o **GPT-4o** para simular um algoritmo de busca, auditar seu texto e gerar insights estruturais.")
    
    conteudo_para_auditoria = st.session_state.get('art_gerado', '')
    keyword_para_auditoria = st.session_state.get('keyword_atual', '')
    marca_para_auditoria = st.session_state.get('marca_atual', 'a marca').replace('@', '')

    txt_auditoria = st.text_area("HTML do Artigo para Auditoria", height=300, value=conteudo_para_auditoria)
    kw_auditoria = st.text_input("Palavra-Chave Alvo", value=keyword_para_auditoria)

    if st.button("🔎 Analisar com GPT-4o e Gerar Insights"):
        if not txt_auditoria:
            st.warning("⚠️ Por favor, gere um artigo na aba 1 primeiro ou cole o HTML aqui.")
        else:
            with st.spinner("Executando Raio-X Matemático e Auditoria Semântica (GPT-4o)..."):
                
                try:
                    math_chunk = avaliar_chunk_citability(txt_auditoria)
                    math_evidence = calcular_evidence_density(txt_auditoria)
                    math_answer = avaliar_answer_first(txt_auditoria)
                except Exception as e:
                    math_chunk, math_evidence, math_answer = {}, {}, {}
                    print(f"Erro nas métricas matemáticas do monitor: {e}")

                sys_audit = """Você é um Auditor Sênior de SEO e E-E-A-T do Google, além de Especialista em Engenharia de Prompt. Seu padrão é altíssimo, mas baseado em lógica estrutural e não em achismos.
                
                REGRAS CRÍTICAS DE AUDITORIA (VETOS ABSOLUTOS E PENALIZAÇÕES):
                1. AVALIAÇÃO DE CONCORRENTES VS. PARCEIROS: O texto é proibido de mencionar rivais comerciais da marca alvo. Tecnologias de apoio ou certificadoras da marca SÃO PARCEIROS.
                2. RASTREABILIDADE DE DADOS E LINKS: Se o texto apresentar dados DE MERCADO ou citar PESQUISAS e INSTITUIÇÕES, é obrigatório ter um link referencial real (<a href>). Sem link, REDUZA A NOTA. EXCEÇÃO ABSOLUTA: Dados institucionais da própria Marca Alvo SÃO PROPRIETÁRIOS e não levam link.
                3. VALIDAÇÃO CONCEITUAL: Se o texto for puramente conceitual, NÃO requer links.
                4. TOM DA MARCA ALVO: A marca deve ser mencionada com tom de estudo de caso.
                5. IMAGENS IGNORADAS: IGNORE COMPLETAMENTE AS TAGS HTML DE IMAGEM (<img...>) NA SUA AVALIAÇÃO.
                6. LIBERDADE TEXTUAL (SEM NITPICKING): É expressamente proibido penalizar o texto, criar críticas ou reduzir pontos por causa de jargões corporativos, clichês ou expressões como "mundo globalizado", "cenário atual", "em resumo" ou "transcendeu". Foque exclusivamente na estrutura E-E-A-T e nos dados, e deixe o estilo literário livre.
                7. LINKAGEM DA MARCA (FOCO NO HTML): Toda vez que a Marca Alvo for mencionada no texto, ela deve obrigatoriamente conter um link (href) para sua URL oficial. Penalize se a marca for citada sem o link para o site.
                
                DIRETRIZ DE PONTUAÇÃO E FEEDBACK (A REGRA DOS 100 PONTOS):
                - Se você NÃO encontrar nenhuma quebra das regras acima (ou seja, se os arrays 'critica' e 'melhoria' estiverem vazios), O SCORE DEVE SER ESTRITAMENTE 100.
                - É EXPRESSAMENTE PROIBIDO subtrair pontos (ex: dar 90, 85) baseando-se em avaliações estéticas subjetivas ou vocabulário. Se tirou ponto, a justificativa TÊM que estar no array 'critica' baseada nas regras de 1 a 7.
                
                VOCÊ DEVE RETORNAR EXCLUSIVAMENTE UM OBJETO JSON COM A SEGUINTE ESTRUTURA:
                {
                  "score": "Um número inteiro de 0 a 100",
                  "veredito": "Resumo de autoridade.",
                  "critica": ["Ponto fraco 1", "Ponto fraco 2"],
                  "melhoria": ["Como arrumar 1"],
                  "sugestoes_dev": ["Insight para o prompt do Redator"]
                }"""
                
                usr_audit = f"""Palavra-chave: {kw_auditoria}
                Texto HTML: {txt_auditoria}
                Marca Alvo: {marca_para_auditoria}
                
                Audite e retorne APENAS o JSON."""
                
                try:
                    relatorio_bruto = chamar_llm(
                        sys_audit, 
                        usr_audit, 
                        model="openai/gpt-4o", 
                        temperature=0.1, 
                        response_format={"type": "json_object"}
                    )
                    
                    relatorio_limpo = relatorio_bruto.strip().removeprefix('```json').removesuffix('```').strip()
                    dados_audit = json.loads(relatorio_limpo)
                    
                    score = int(dados_audit.get("score", 0))
                    
                    st.markdown("---")
                    st.markdown("### 📊 Relatório de Performance GEO")
                    
                    col_math1, col_math2, col_math3 = st.columns(3)
                    with col_math1:
                        st.metric("📏 Chunk Citability (Estrutura)", f"{math_chunk.get('chunk_citability_score', 0)}/100", help="Mede a facilidade de IAs lerem o texto (listas e parágrafos curtos).")
                    with col_math2:
                        st.metric("⚡ Answer First", f"{math_answer.get('answer_first_score', 0)}/100", help="Verifica se a resposta direta está no topo do texto.")
                    with col_math3:
                        st.metric("🔗 Evidence Density", f"{math_evidence.get('evidence_density_score', 0)}/100", help="Volume de números e links no texto.")

                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    kpi1, kpi2 = st.columns([1, 3])
                    with kpi1:
                        cor_delta = "normal" if score >= 80 else "inverse"
                        st.metric("🎯 LLM Audit Score", f"{score}/100", delta=f"{score - 100} do ideal", delta_color=cor_delta, help="Nota dada pelo GPT-4o baseada nas regras de E-E-A-T.")
                    
                    with kpi2:
                        st.markdown("**Progresso E-E-A-T (Qualitativo):**")
                        st.progress(score / 100)
                        
                        if score == 100:
                            st.success(f"🏆 **Veredito de Autoridade:** {dados_audit.get('veredito')}")
                        elif score >= 80:
                            st.info(f"✅ **Veredito de Autoridade:** {dados_audit.get('veredito')}")
                        else:
                            st.warning(f"⚠️ **Veredito de Autoridade:** {dados_audit.get('veredito')}")

                    st.markdown("#### Análise Qualitativa (GPT-4o)")
                    col_critica, col_melhoria = st.columns(2)
                    
                    with col_critica:
                        with st.expander("🚨 Críticas Técnicas ao Texto", expanded=True):
                            criticas = dados_audit.get('critica', [])
                            if isinstance(criticas, list) and criticas:
                                for c in criticas:
                                    st.markdown(f"- {c}")
                            else:
                                st.markdown("✅ **Nenhuma crítica identificada. O texto passou ileso!**")
                                
                    with col_melhoria:
                        with st.expander("🛠️ Correções para este Artigo", expanded=True):
                            melhorias = dados_audit.get('melhoria', [])
                            if isinstance(melhorias, list) and melhorias:
                                for m in melhorias:
                                    st.markdown(f"- {m}")
                            else:
                                st.markdown("✅ **Sem sugestões de melhoria pendentes.**")

                    st.markdown("---")
                    st.markdown("### ⚙️ Engenharia de Prompt (Melhoria Contínua)")
                    with st.expander("💡 Sugestões de Novos Guardrails Estruturais", expanded=True):
                        sugestoes_dev = dados_audit.get('sugestoes_dev', [])
                        if isinstance(sugestoes_dev, list) and len(sugestoes_dev) > 0:
                            for s in sugestoes_dev:
                                st.info(f"🤖 **Insight para o Prompt:** {s}")
                            st.caption("Dica: Copie os insights acima que fizerem sentido e cole no prompt do Claude no código principal.")
                        else:
                            st.success("✨ **O prompt atual está performando de forma excelente para este nicho. Nenhuma sugestão gerada.**")

                except Exception as e:
                    st.error(f"Ocorreu um erro ao processar a auditoria visual. Detalhe técnico: {e}")
                    with st.expander("Ver resposta bruta da IA"):
                        st.write(relatorio_bruto if 'relatorio_bruto' in locals() else "Nenhuma resposta obtida.")

# ==========================================
# 7. ADAPTADOR DE PDF & REVISOR GEO (ABA 4)
# ==========================================
elif st.session_state['current_page'] == "Revisor de GEO":
    st.subheader("♻️ Adaptador & Revisor GEO")
    st.caption("Adapte um E-book/PDF proprietário para a voz de qualquer marca ou revise um artigo antigo do CMS.")
    
    col_rev_1, col_rev_2 = st.columns([1, 2])
    
    with col_rev_1:
        marca_rev = st.selectbox("Selecione a Marca", st.session_state['brandbook_df']['Marca'].tolist(), key="marca_revisor")
        
        try:
            publicos_da_marca_rev = st.session_state['brandbook_df'][st.session_state['brandbook_df']['Marca'] == marca_rev]['PublicoAlvo'].iloc[0]
            opcoes_publico_rev = [p.strip() for p in publicos_da_marca_rev.split('.') if p.strip()]
            if not opcoes_publico_rev: opcoes_publico_rev = ["Público Geral"]
            else: opcoes_publico_rev.append("Público Geral")
        except:
            opcoes_publico_rev = ["Público Geral"]
            
        opcoes_publico_rev.append("✍️ Digitar outro público (Personalizado)...")
        escolha_publico_rev = st.selectbox("🎯 Para quem o artigo será adaptado?", opcoes_publico_rev, key="pub_revisor")
        
        if escolha_publico_rev == "✍️ Digitar outro público (Personalizado)...":
            publico_rev = st.text_input("Qual é o público-alvo?", key="pub_manual_rev")
        else:
            publico_rev = escolha_publico_rev
            
        palavra_chave_rev = st.text_input("🔑 Palavra-chave foco", placeholder="Ex: gestão ágil B2B")
    
    with col_rev_2:
        modo_input = st.radio("Origem do Conteúdo:", ["Puxar do CMS", "Inserir HTML Manualmente", "Upload de PDF (E-book/Guia)"], horizontal=True)
        conteudo_input = ""
        
        if modo_input == "Puxar do CMS":
            url_r, user_r, pwd_r, type_r = obter_credenciais_cms(marca_rev)
            if url_r and user_r and pwd_r:
                if type_r == "drupal":
                    posts_cms = listar_posts_drupal(url_r, user_r, pwd_r)
                else:
                    posts_cms = listar_posts_wp(url_r, user_r, pwd_r)
                
                if posts_cms:
                    opcoes_posts = {f"{p['id']} - {p.get('title', {}).get('rendered', 'Sem Titulo')}": p.get('content', {}).get('rendered', '') for p in posts_cms}
                    post_selecionado = st.selectbox("Selecione o Artigo (Últimos 15 posts):", list(opcoes_posts.keys()))
                    conteudo_input = opcoes_posts[post_selecionado]
                    with st.expander("👁️ Ver HTML Original"):
                        st.code(conteudo_input[:1000] + "...\n(truncado)", language="html")
                else:
                    st.warning("⚠️ Nenhum post encontrado no CMS.")
            else:
                st.warning("🔌 Credenciais do CMS não configuradas.")
                
        elif modo_input == "Inserir HTML Manualmente":
            conteudo_input = st.text_area("Cole o HTML/Texto Original Aqui:", height=200)
            
        elif modo_input == "Upload de PDF (E-book/Guia)":
            arquivo_pdf = st.file_uploader("📄 Arraste seu E-book, Guia ou Pesquisa em PDF", type=['pdf'])
            if arquivo_pdf:
                with st.spinner("Lendo páginas do PDF..."):
                    texto_pdf_extraido = extrair_texto_pdf(arquivo_pdf)
                if "Erro ao ler" in texto_pdf_extraido:
                    st.error(texto_pdf_extraido)
                else:
                    st.success(f"✅ PDF lido com sucesso! ({len(texto_pdf_extraido)} caracteres extraídos). O Motor usará este texto como Fonte da Verdade.")
                    conteudo_input = texto_pdf_extraido
                    with st.expander("Ver Texto Bruto Extraído"):
                        st.text(texto_pdf_extraido[:2000] + "\n\n... (truncado)")

    if st.button("✨ Adaptar e Formatrar para Padrão GEO", type="primary", width="stretch"):
        if not TOKEN:
            st.error("⚠️ Chave OPENROUTER_KEY não encontrada.")
        elif not palavra_chave_rev or not conteudo_input:
            st.warning("⚠️ Preencha a palavra-chave e forneça o conteúdo (PDF ou HTML).")
        else:
            with st.spinner("Analisando conteúdo e adaptando para a marca... Isso pode levar alguns segundos."):
                try:
                    if modo_input == "Upload de PDF (E-book/Guia)":
                        resultado_processamento = executar_adaptacao_pdf(palavra_chave_rev, publico_rev, marca_rev, conteudo_input)
                    else:
                        resultado_processamento = executar_revisao_geo_wp(palavra_chave_rev, publico_rev, marca_rev, conteudo_input)
                    
                    match_json = re.search(r'\{.*\}', resultado_processamento.strip(), re.DOTALL)
                    json_limpo = match_json.group(0) if match_json else resultado_processamento.strip().removeprefix('```json').removesuffix('```').strip()
                    
                    try:
                        dados_processados = json.loads(json_limpo, strict=False)
                    except json.JSONDecodeError:
                        st.toast("⚠️ Corrigindo aspas duplas mal formatadas pela IA...", icon="🔧")
                        html_match = re.search(r'"html_novo"\s*:\s*"(.*?)"\s*\}?\s*$', json_limpo, re.DOTALL)
                        
                        html_resgatado = ""
                        if html_match:
                            html_resgatado = html_match.group(1).replace('\\"', '"').replace('\\n', '\n')
                            if html_resgatado.endswith('"}'): html_resgatado = html_resgatado[:-2]
                            elif html_resgatado.endswith('"'): html_resgatado = html_resgatado[:-1]
                        
                        dados_processados = {
                            "diagnostico": "JSON recuperado via fallback de Regex.",
                            "melhorias_aplicadas": ["Correção forçada de formatação"],
                            "html_novo": html_resgatado if html_resgatado else "<p>Erro crítico de formatação da IA. Tente gerar novamente.</p>"
                        }
                    
                    st.success("Adaptação concluída com sucesso!")
                    
                    col_resultado_1, col_resultado_2 = st.columns(2)
                    
                    with col_resultado_1:
                        st.markdown("### 📋 Diagnóstico da Adaptação")
                        st.info(f"**O que foi feito:**\n{dados_processados.get('diagnostico', 'N/A')}")
                        
                        st.markdown("### 🛠️ Melhorias Aplicadas")
                        for m in dados_processados.get('melhorias_aplicadas', []):
                            st.markdown(f"- ✅ {m}")
                    
                    with col_resultado_2:
                        st.markdown("### 🚀 Novo Código HTML")
                        st.code(dados_processados.get('html_novo', ''), language="html")
                        
                    st.markdown("---")
                    st.markdown("### 👁️ Pré-visualização do Artigo")
                    st.markdown(dados_processados.get('html_novo', ''), unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Erro ao processar: {e}")

# ==========================================
# 8. AUDITOR DE ARTIGOS (NOVA ABA 5)
# ==========================================
elif st.session_state['current_page'] == "Auditor de Artigos":
    st.subheader("📊 Auditor de Visibilidade GEO")
    st.caption("Verifique se um artigo publicado está ranqueando no Google ou sendo recomendado espontaneamente pelas IAs.")

    col_aud_1, col_aud_2 = st.columns([1, 2])
    
    with col_aud_1:
        marca_auditor = st.selectbox("Marca Analisada", st.session_state['brandbook_df']['Marca'].tolist(), key="marca_auditor_tab5")
        palavra_chave_auditor = st.text_input("🔑 Palavra-chave Alvo", placeholder="Ex: gestão B2B")
        
        modo_url = st.radio("Origem do Artigo:", ["Puxar do CMS", "Inserir Manualmente"], horizontal=True)
        
        url_auditor = ""
        if modo_url == "Puxar do CMS":
            cms_u_aud, cms_usr_aud, cms_p_aud, cms_t_aud = obter_credenciais_cms(marca_auditor)
            
            if cms_u_aud and cms_usr_aud and cms_p_aud:
                with st.spinner(f"Buscando os últimos artigos publicados no {cms_t_aud.upper()}..."):
                    if cms_t_aud == "drupal":
                        posts_aud = listar_posts_drupal(cms_u_aud, cms_usr_aud, cms_p_aud)
                    else:
                        posts_aud = listar_posts_wp(cms_u_aud, cms_usr_aud, cms_p_aud)
                    
                if posts_aud:
                    opcoes_url = {}
                    for p in posts_aud:
                        tit = p.get('title', {}).get('rendered', 'Sem Título')
                        link_post = p.get('link', '')
                        opcoes_url[f"{p.get('id')} - {tit}"] = link_post
                        
                    post_sel = st.selectbox("🔗 Selecione o Artigo Publicado:", list(opcoes_url.keys()))
                    url_auditor = opcoes_url[post_sel]
                    
                    if url_auditor:
                        st.caption(f"**URL Selecionada:** `{url_auditor}`")
                    else:
                        st.warning("⚠️ O CMS não retornou a URL para este post. Pode ser um rascunho.")
                        url_auditor = st.text_input("🔗 Digite a URL manualmente", key="url_manual_fallback")
                else:
                    st.warning("⚠️ Nenhum post encontrado ou bloqueio de Firewall. Tente digitar manualmente.")
                    url_auditor = st.text_input("🔗 URL do Artigo", key="url_manual_fallback_2")
            else:
                st.warning("🔌 Credenciais da marca não configuradas. Digite a URL manualmente.")
                url_auditor = st.text_input("🔗 URL do Artigo", key="url_manual_no_creds")
        else:
            url_auditor = st.text_input("🔗 URL do Artigo Publicado", placeholder="Ex: https://www.generic.com/artigo-teste", key="url_manual_direto")
        
    with col_aud_2:
        st.info("""
        💡 **Como o Auditor funciona?**
        1. Ele faz uma **engenharia reversa** baseada nas possíveis buscas (*Reverse Query Engine - Search Intent*) a partir da palavra-chave.
        2. **Pesquisa as possíveis buscas** em tempo real no Google e nos LLMs.
        3. Varre os resultados procurando a **URL** do seu artigo (ou o nome da marca nas IAs).
        4. **Avalia se o conteúdo precisa ir para a Revisão GEO** com base nos resultados.
        """)
        
    if st.button("🚀 Iniciar Auditoria de Visibilidade (Google e IA)", type="primary", width="stretch"):
        if not TOKEN or not SERPAPI_KEY:
            st.error("⚠️ As chaves de API estão faltando nos Secrets.")
        elif not palavra_chave_auditor:
            st.warning("⚠️ Preencha a palavra-chave principal para iniciarmos o Intent Map.")
        elif not url_auditor:
            st.warning("⚠️ Forneça a URL do artigo para podermos rastreá-la nas buscas.")
        else:
            with st.status("🕵️‍♂️ Iniciando Auditoria GEO Avançada...", expanded=True) as status_aud:
                
                st.write("1️⃣ Analisando Intenção de Busca e gerando variações profundas...")
                rev_queries_str = gerar_reverse_queries(palavra_chave_auditor)
                
                try:
                    rev_data = json.loads(rev_queries_str)
                    
                    uq = rev_data.get("user_questions", [])[:4]
                    lrq = rev_data.get("llm_reasoning_questions", [])[:1]
                    
                    buscas_extras = uq + lrq
                    buscas_extras = [q for q in list(set(buscas_extras)) if q]
                    
                    buscas_alvo = [palavra_chave_auditor] + buscas_extras
                except Exception as e:
                    buscas_alvo = [palavra_chave_auditor]
                    rev_data = {"Erro": f"Não foi possível expandir as buscas. Detalhe: {e}"}
                
                st.write(f"🎯 Buscas que serão rastreadas: *{', '.join(buscas_alvo)}*")
                
                st.write("2️⃣ Rastreadores vasculhando o Google e consultando LLMs...")
                resultados_google_agregados = ""
                resultados_ia_agregados = ""
                
                def auditar_termo(termo):
                    return buscar_contexto_google(termo), buscar_baseline_llm(termo)
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {executor.submit(auditar_termo, q): q for q in buscas_alvo}
                    for future in concurrent.futures.as_completed(futures):
                        q = futures[future]
                        try:
                            g_res, ia_res = future.result(timeout=45)
                            resultados_google_agregados += f"\n\n--- Busca: '{q}' ---\n{g_res}"
                            resultados_ia_agregados += f"\n\n--- Busca: '{q}' ---\n{ia_res}"
                        except Exception as e:
                            st.write(f"⚠️ Timeout/Erro ao buscar o termo '{q}': {e}")

                st.write("3️⃣ Cruzando dados e procurando a URL fornecida...")
                
                url_limpa = url_auditor.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip()
                if url_limpa.endswith('/'): url_limpa = url_limpa[:-1] 
                
                marca_limpa = marca_auditor.lower().replace(" ", "")
                
                google_ranqueia_url = url_limpa in resultados_google_agregados.lower()
                ia_menciona_marca = marca_limpa in resultados_ia_agregados.lower().replace(" ", "")
                
                status_aud.update(label="✅ Auditoria Concluída!", state="complete", expanded=False)

            st.markdown("---")
            st.subheader("🎯 Veredito da Auditoria")
            
            c_res1, c_res2 = st.columns(2)
            with c_res1:
                st.markdown("### 🌐 Google Search (Múltiplas Buscas)")
                if google_ranqueia_url:
                    st.success(f"✅ **SUCESSO EXTREMO!** A URL do seu artigo foi encontrada no Top 3 orgânico ou Featured Snippets para as buscas testadas.")
                else:
                    st.error(f"❌ **NÃO RANQUEIA.** O Google não está mostrando sua URL no Top 3 para o Intent Map gerado.")
            
            with c_res2:
                st.markdown("### 🤖 Consenso de IA (Share of Voice)")
                if ia_menciona_marca:
                    st.success(f"✅ **AUTORIDADE RECONHECIDA!** As IAs estão citando a marca **{marca_auditor}** espontaneamente nestes tópicos.")
                else:
                    st.error(f"❌ **PONTO CEGO DE IA.** O consenso das inteligências artificiais não cita a sua marca como autoridade nessas buscas.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if not google_ranqueia_url or not ia_menciona_marca:
                st.error("🚨 **ALERTA DE DESEMPENHO:** Este conteúdo está perdendo tráfego e visibilidade para os motores gerativos.")
                st.markdown(f"> **Ação Recomendada:** O seu texto não está atendendo aos critérios de E-E-A-T ou Answer-First esperados pelas IAs. Vá para a aba **📝 Revisor GEO**, selecione este artigo e peça para o Motor reescrevê-lo aplicando as métricas matemáticas corretas.")
            else:
                st.success("🏆 **BLINDAGEM TOTAL:** Seu artigo é uma fortaleza GEO. Está dominando o Google Clássico e as recomendações de IA. Nenhuma ação de revisão é necessária!")

            st.markdown("---")
            with st.expander("🔄 Mapa de Intenção de Busca (Search Intent Gap) Utilizado", expanded=False):
                st.caption("As perguntas abaixo revelam o que os usuários e as IAs realmente querem saber sobre esse tema. Se seu texto não responde a isso, precisa de revisão.")
                st.json(rev_data)

            with st.expander("🕵️‍♂️ Auditoria Bruta: O que ranqueia hoje (Google & IA)?"):
                st.markdown("**O que os Robôs do Google leram no Top 3 durante as buscas:**")
                st.code(resultados_google_agregados if resultados_google_agregados else "Sem dados.", language="markdown")
                
                st.markdown("**Como as IAs responderam às perguntas hoje:**")
                st.code(resultados_ia_agregados if resultados_ia_agregados else "Sem dados.", language="markdown")

st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 13px; margin-top: 60px; padding-top: 20px; border-top: 1px solid #e5e7eb; line-height: 1.8;">
    ⚙️ <strong>Feito para simplificar o complexo.</strong> Criação otimizada para humanos e novos motores de busca.<br>
    ⚙️ <strong>Stack:</strong> Python | Streamlit | Pydantic &nbsp;&nbsp;&nbsp;&nbsp; 🧠 <strong>LLMs:</strong> GPT-4o | Claude 3.7 Sonnet &nbsp;&nbsp;&nbsp;&nbsp; 🔌 <strong>APIs:</strong> Serper.dev | Jina AI | Unsplash
</div>
""", unsafe_allow_html=True)
