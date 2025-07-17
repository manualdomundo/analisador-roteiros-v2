import streamlit as st
import os
import asyncio
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

def executar_analise_sequencial(roteiro_content, modelo_gpt):
    """Executa análise sequencial do roteiro"""
    # Verificar se há critérios
    if not os.path.exists('criterios.txt'):
        st.error("❌ Arquivo criterios.txt não encontrado!")
        st.stop()
    
    # Inicializar analisador
    try:
        analisador = AnalisadorRoteiro(modelo=modelo_gpt.strip())
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
    with st.spinner("Analisando roteiro (sequencial)..."):
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
    mostrar_resultados(resultados, analisador, modelo_gpt)

def executar_analise_paralela(roteiro_content, modelo_gpt):
    """Executa análise paralela do roteiro"""
    # Verificar se há critérios
    if not os.path.exists('criterios.txt'):
        st.error("❌ Arquivo criterios.txt não encontrado!")
        st.stop()
    
    # Inicializar analisador
    try:
        analisador = AnalisadorRoteiro(modelo=modelo_gpt.strip())
    except Exception as e:
        st.error(f"❌ Erro ao inicializar analisador: {e}")
        st.stop()
    
    # Ler critérios
    criterios = analisador.ler_criterios()
    if not criterios:
        st.error("❌ Nenhum critério encontrado!")
        st.stop()
    
    # Executar análise paralela
    with st.spinner("Analisando roteiro (paralelo)..."):
        # Criar um arquivo temporário para o roteiro
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(roteiro_content)
            arquivo_temp = f.name
        
        try:
            # Executar análise assíncrona
            resultados = asyncio.run(analisador.analisar_roteiro_completo_async(arquivo_temp))
        finally:
            # Limpar arquivo temporário
            os.unlink(arquivo_temp)
    
    # Mostrar resultados
    mostrar_resultados(resultados, analisador, modelo_gpt)

def mostrar_resultados(resultados, analisador, modelo_gpt):
    """Mostra os resultados da análise"""
    st.success("✅ Análise concluída!")
    st.header("📊 Relatório de Análise")
    st.caption(f"Modelo usado: **{modelo_gpt}**")
    
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
    
    # Seção para editar roteiro
    st.markdown("---")
    st.header("✏️ Editar Roteiro")
    st.markdown("**Dica:** Edite o texto abaixo com base no relatório e analise novamente!")
    
    # Caixa de texto editável com o roteiro atual
    roteiro_editado = st.text_area(
        "Roteiro editado:",
        value=st.session_state.roteiro_content,
        height=300,
        key="roteiro_editado",
        help="Edite seu roteiro com base nas sugestões do relatório"
    )
    
    # Botão para analisar novamente
    if st.button("🔄 Analisar Roteiro Editado", type="secondary", use_container_width=True):
        if roteiro_editado.strip():
            # Atualizar session state com texto editado
            st.session_state.roteiro_content = roteiro_editado
            # Reanalizar com texto editado
            st.rerun()
        else:
            st.error("❌ O roteiro editado não pode estar vazio!")
    
    # Seção de logs das requisições
    st.markdown("---")
    st.header("📊 Log de Requisições à API")
    
    # Calcular estatísticas totais
    total_tokens = sum(log.get('tokens_total', 0) for log in analisador.log_requisicoes)
    total_requisicoes = len(analisador.log_requisicoes)
    
    # Métricas de uso
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Requisições", total_requisicoes)
    with col2:
        st.metric("Total de Tokens", total_tokens)
    with col3:
        # Estimativa de custo (aproximada)
        if "gpt-4o" in modelo_gpt and "mini" not in modelo_gpt:
            custo_estimado = (total_tokens / 1000) * 0.015  # $0.015 por 1K tokens
        elif "gpt-4o-mini" in modelo_gpt:
            custo_estimado = (total_tokens / 1000) * 0.0015  # $0.0015 por 1K tokens
        elif "gpt-4" in modelo_gpt:
            custo_estimado = (total_tokens / 1000) * 0.03  # $0.03 por 1K tokens
        elif "gpt-3.5-turbo" in modelo_gpt:
            custo_estimado = (total_tokens / 1000) * 0.002  # $0.002 por 1K tokens
        else:
            custo_estimado = (total_tokens / 1000) * 0.01  # Estimativa genérica
        
        st.metric("Custo Estimado", f"${custo_estimado:.4f}")
    
    # Tabela detalhada dos logs
    if st.expander("🔍 Detalhes das Requisições", expanded=False):
        for i, log in enumerate(analisador.log_requisicoes, 1):
            st.subheader(f"Requisição {i} - {log['timestamp']}")
            
            # Informações básicas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Modelo:** {log['modelo']}")
                st.write(f"**Tipo:** {log['tipo']}")
            with col2:
                st.write(f"**Tokens Input:** {log['tokens_input']}")
                st.write(f"**Tokens Output:** {log['tokens_output']}")
            with col3:
                st.write(f"**Tokens Total:** {log['tokens_total']}")
                st.write(f"**Chars Prompt:** {log['prompt_chars']}")
            
            # Mostrar prompt (truncado)
            st.write("**Prompt:**")
            st.code(log['prompt'], language="text")
            
            # Mostrar resposta
            st.write("**Resposta:**")
            if log['tipo'].startswith('ERRO'):
                st.error(log['resposta'])
            else:
                st.success(log['resposta'])
            
            st.markdown("---")
    
    # Recomendações de otimização
    st.subheader("💡 Recomendações de Otimização")
    
    if total_tokens > 10000:
        st.warning("⚠️ Alto uso de tokens! Considere:")
        st.markdown("- Usar GPT-3.5-turbo para economizar")
        st.markdown("- Roteiros mais curtos")
        st.markdown("- Menos critérios por análise")
    elif total_tokens > 5000:
        st.info("ℹ️ Uso moderado de tokens. Considere usar GPT-4o-mini para equilibrar custo e qualidade.")
    else:
        st.success("✅ Uso eficiente de tokens!")

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
            placeholder="sk-proj-...",
            help="Sua chave da API OpenAI"
        )
        
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key
        
        st.markdown("---")
        
        # Seletor de modelo GPT
        st.header("🤖 Modelo GPT")
        
        # Opção entre predefinidos ou personalizado
        tipo_modelo = st.radio(
            "Escolha o tipo:",
            options=["Modelos Predefinidos", "Modelo Personalizado"],
            index=0,
            help="Use modelos predefinidos para facilidade ou digite um modelo específico"
        )
        
        if tipo_modelo == "Modelos Predefinidos":
            modelo_gpt = st.selectbox(
                "Escolha o modelo:",
                options=["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "gpt-4-turbo"],
                index=0,
                help="GPT-4o-mini: Equilibrado (padrão) | GPT-4o: Mais preciso | GPT-3.5-turbo: Econômico | GPT-4-turbo: Versão anterior"
            )
            
            # Mostrar informações do modelo
            if modelo_gpt == "gpt-4o-mini":
                st.info("⚡ **GPT-4o-mini**: Equilibrio entre qualidade e custo (padrão)")
            elif modelo_gpt == "gpt-4o":
                st.info("🎯 **GPT-4o**: Máxima precisão e qualidade")
            elif modelo_gpt == "gpt-4-turbo":
                st.info("🚀 **GPT-4-turbo**: Versão anterior do GPT-4")
            else:
                st.info("💰 **GPT-3.5-turbo**: Mais econômico")
        else:
            modelo_gpt = st.text_input(
                "Digite o modelo:",
                value="gpt-4o-mini",
                help="Digite qualquer modelo OpenAI válido (ex: gpt-4, gpt-3.5-turbo-1106, etc.)",
                placeholder="gpt-4o-mini"
            )
            
            if modelo_gpt:
                st.info(f"🛠️ **Modelo Personalizado**: {modelo_gpt}")
            else:
                st.warning("⚠️ Digite um modelo válido")
            
            # Sugestões de modelos
            with st.expander("📋 Modelos Comuns", expanded=False):
                st.markdown("**GPT-4 Family:**")
                st.markdown("- `gpt-4o` - Mais recente")
                st.markdown("- `gpt-4o-mini` - Versão menor")
                st.markdown("- `gpt-4-turbo` - Versão anterior")
                st.markdown("- `gpt-4` - Versão original")
                
                st.markdown("**GPT-3.5 Family:**")
                st.markdown("- `gpt-3.5-turbo` - Padrão")
                st.markdown("- `gpt-3.5-turbo-1106` - Versão específica")
                st.markdown("- `gpt-3.5-turbo-16k` - Contexto maior")
                
                st.markdown("**Outros:**")
                st.markdown("- `gpt-4-32k` - Contexto muito grande")
                st.markdown("- `gpt-3.5-turbo-instruct` - Versão instruct")
        
        st.markdown("---")
        st.markdown("### 📊 Como usar:")
        st.markdown("1. Insira sua chave OpenAI")
        st.markdown("2. Escolha o modelo GPT")
        st.markdown("3. Cole/digite seu roteiro")
        st.markdown("4. Clique em 'Analisar Roteiro'")
        st.markdown("5. Veja o relatório e edite o texto")
        st.markdown("6. Analise novamente para refinar")
    
    # Verificar se API key está configurada
    if not os.getenv('OPENAI_API_KEY'):
        st.error("❌ Configure sua chave OpenAI API na barra lateral!")
        st.stop()
    
    # Verificar se modelo foi especificado
    if not modelo_gpt or modelo_gpt.strip() == "":
        st.error("❌ Especifique um modelo GPT na barra lateral!")
        st.stop()
    
    # Caixa de texto para roteiro
    st.header("📝 Roteiro do Vídeo")
    
    # Texto de exemplo/placeholder
    texto_exemplo = """[EXEMPLO - Substitua pelo seu roteiro]

[ABERTURA - 0:00-0:15]
Olá pessoal! Vocês sabiam que...

[DESENVOLVIMENTO - 0:15-2:00]
Primeiro vamos entender...

[FECHAMENTO - 2:00-2:30]
E aí, gostaram? Deixem um like e se inscrevam!"""
    
    # Inicializar session state para o roteiro
    if 'roteiro_content' not in st.session_state:
        st.session_state.roteiro_content = ""
    
    # Caixa de texto editável
    roteiro_content = st.text_area(
        "Cole ou digite seu roteiro aqui:",
        value=st.session_state.roteiro_content,
        height=300,
        placeholder=texto_exemplo,
        help="Cole seu roteiro aqui ou digite diretamente. Você pode editar o texto após a análise.",
        key="roteiro_input"
    )
    
    # Atualizar session state
    st.session_state.roteiro_content = roteiro_content
    
    # Mostrar estatísticas do roteiro
    if roteiro_content:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Caracteres", len(roteiro_content))
        with col2:
            palavras = len(roteiro_content.split())
            st.metric("Palavras", palavras)
        with col3:
            linhas = len(roteiro_content.splitlines())
            st.metric("Linhas", linhas)
        
        # Botão para analisar
        if st.button("🔍 Analisar Roteiro", type="primary", use_container_width=True):
            executar_analise_paralela(roteiro_content, modelo_gpt)
    
    else:
        st.warning("⚠️ Digite ou cole seu roteiro para começar a análise!")

if __name__ == "__main__":
    main()