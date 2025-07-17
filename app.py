import streamlit as st
import os
from io import StringIO
from analisador import AnalisadorRoteiro

def carregar_env():
    """Carrega variáveis do arquivo .env"""
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        pass

def main():
    st.set_page_config(
        page_title="Analisador de Roteiros",
        page_icon="🎬",
        layout="wide"
    )
    
    # Carregar configurações
    carregar_env()
    
    # Título
    st.title("🎬 Analisador de Roteiros de Vídeo")
    st.markdown("---")
    
    # Sidebar para configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        # Campo para API Key
        api_key = st.text_input(
            "Chave OpenAI API", 
            type="password",
            value=os.getenv('OPENAI_API_KEY', ''),
            help="Sua chave da API OpenAI"
        )
        
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key
        
        st.markdown("---")
        st.markdown("### 📊 Como usar:")
        st.markdown("1. Insira sua chave OpenAI")
        st.markdown("2. Faça upload do roteiro (.txt)")
        st.markdown("3. Clique em 'Analisar Roteiro'")
        st.markdown("4. Veja o relatório na tela")
    
    # Verificar se API key está configurada
    if not os.getenv('OPENAI_API_KEY'):
        st.error("❌ Configure sua chave OpenAI API na barra lateral!")
        st.stop()
    
    # Upload do arquivo
    st.header("📁 Upload do Roteiro")
    uploaded_file = st.file_uploader(
        "Escolha um arquivo de roteiro (.txt)", 
        type=['txt'],
        help="Faça upload do arquivo de texto com seu roteiro"
    )
    
    if uploaded_file is not None:
        # Ler conteúdo do arquivo
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        roteiro_content = stringio.read()
        
        # Mostrar prévia do roteiro
        st.header("📄 Prévia do Roteiro")
        with st.expander("Ver conteúdo do roteiro", expanded=False):
            st.text_area("Conteúdo:", roteiro_content, height=200, disabled=True)
        
        st.markdown(f"**Tamanho:** {len(roteiro_content)} caracteres")
        
        # Botão para analisar
        if st.button("🔍 Analisar Roteiro", type="primary", use_container_width=True):
            
            # Verificar se há critérios
            if not os.path.exists('criterios.txt'):
                st.error("❌ Arquivo criterios.txt não encontrado!")
                st.stop()
            
            # Inicializar analisador
            try:
                analisador = AnalisadorRoteiro()
            except Exception as e:
                st.error(f"❌ Erro ao inicializar analisador: {e}")
                st.stop()
            
            # Ler critérios
            criterios = analisador.ler_criterios()
            if not criterios:
                st.error("❌ Nenhum critério encontrado!")
                st.stop()
            
            # Criar progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Executar análise
            with st.spinner("Analisando roteiro..."):
                resultados = []
                
                for i, criterio in enumerate(criterios):
                    # Atualizar progress
                    progress = (i + 1) / len(criterios)
                    progress_bar.progress(progress)
                    
                    titulo = criterio['titulo'] if isinstance(criterio, dict) else criterio[:50]
                    status_text.text(f"Analisando: {titulo}")
                    
                    # Analisar critério
                    resultado = analisador.analisar_criterio(roteiro_content, criterio)
                    resultados.append({
                        'criterio': criterio,
                        'resultado': resultado
                    })
                
                # Limpar status
                progress_bar.empty()
                status_text.empty()
            
            # Mostrar resultados
            st.success("✅ Análise concluída!")
            st.header("📊 Relatório de Análise")
            
            # Contadores
            aprovados = 0
            total = len(resultados)
            
            for i, resultado in enumerate(resultados, 1):
                criterio = resultado['criterio']
                titulo = criterio['titulo'] if isinstance(criterio, dict) else criterio
                analise = resultado['resultado']
                
                # Verificar se foi aprovado
                if "✅ APROVADO" in analise:
                    aprovados += 1
                    st.success(f"**{i}. {titulo}**")
                    st.write("✅ APROVADO")
                else:
                    if "❌ NÃO ATENDE" in analise:
                        st.error(f"**{i}. {titulo}**")
                    else:
                        st.warning(f"**{i}. {titulo}**")
                    
                    st.write(analise)
                
                st.markdown("---")
            
            # Resumo final
            st.header("📈 Resumo Final")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total de Critérios", total)
            
            with col2:
                st.metric("Aprovados", aprovados, f"{aprovados/total*100:.1f}%")
            
            with col3:
                reprovados = total - aprovados
                st.metric("Precisam Atenção", reprovados, f"{reprovados/total*100:.1f}%")
            
            # Score geral
            score = aprovados / total * 100
            if score >= 80:
                st.success(f"🎉 Excelente! Score: {score:.1f}%")
            elif score >= 60:
                st.warning(f"👍 Bom! Score: {score:.1f}%")
            else:
                st.error(f"📝 Precisa melhorar. Score: {score:.1f}%")

if __name__ == "__main__":
    main()