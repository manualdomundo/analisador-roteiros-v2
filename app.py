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

def carregar_criterios():
    """Carrega critérios do arquivo criterios.txt"""
    try:
        with open('criterios.txt', 'r', encoding='utf-8') as f:
            linhas = [linha.strip() for linha in f.readlines()]
        
        criterios = []
        i = 0
        while i < len(linhas):
            if linhas[i]:  # Linha não vazia (título)
                titulo = linhas[i]
                descricao = ""
                i += 1
                
                # Ler descrição (próximas linhas até linha vazia ou fim)
                while i < len(linhas) and linhas[i]:
                    descricao += linhas[i] + " "
                    i += 1
                
                criterios.append({
                    'titulo': titulo,
                    'descricao': descricao.strip()
                })
            else:
                i += 1
        
        return criterios
    except FileNotFoundError:
        return []


def executar_analise_paralela(roteiro_content, modelo_gpt, criterios_selecionados, criterios_disponiveis):
    """Executa análise paralela do roteiro apenas com critérios selecionados"""
    # Inicializar analisador
    try:
        analisador = AnalisadorRoteiro(modelo=modelo_gpt.strip())
    except Exception as e:
        st.error(f"❌ Erro ao inicializar analisador: {e}")
        st.stop()
    
    # Filtrar apenas critérios selecionados
    criterios_para_analise = []
    for i, criterio in enumerate(criterios_disponiveis):
        if criterios_selecionados.get(i, False):
            criterios_para_analise.append(criterio)
    
    if not criterios_para_analise:
        st.error("❌ Nenhum critério selecionado!")
        st.stop()
    
    # Executar análise paralela
    with st.spinner(f"Analisando roteiro com {len(criterios_para_analise)} critérios..."):
        # Criar um arquivo temporário para o roteiro
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(roteiro_content)
            arquivo_temp = f.name
        
        try:
            # Executar análise assíncrona apenas com critérios selecionados
            resultados = asyncio.run(analisador.analisar_criterios_selecionados_async(arquivo_temp, criterios_para_analise))
        finally:
            # Limpar arquivo temporário
            os.unlink(arquivo_temp)
    
    # Salvar resultados no session_state para persistir na interface
    st.session_state.ultimos_resultados = resultados
    st.session_state.ultimo_analisador = analisador
    st.session_state.ultimo_modelo = modelo_gpt
    
    # Mostrar resultados
    mostrar_resultados(resultados, analisador, modelo_gpt, criterios_disponiveis)

def mostrar_resultados(resultados, analisador, modelo_gpt, criterios_disponiveis):
    """Mostra os resultados da análise"""
    st.success("✅ Análise concluída!")
    st.header("📊 Relatório de Análise")
    st.caption(f"Modelo usado: **{modelo_gpt}**")
    
    # Contadores
    aprovados = 0
    total = len(resultados)
    
    # Inicializar estado para próxima análise se não existir
    if 'proxima_analise_criterios' not in st.session_state:
        st.session_state.proxima_analise_criterios = {}
    
    st.markdown("**📋 Resultados por critério:**")
    st.markdown("*Desmarque critérios aprovados ou marque os que precisam de nova análise*")
    
    for i, resultado in enumerate(resultados, 1):
        criterio = resultado['criterio']
        titulo = criterio['titulo'] if isinstance(criterio, dict) else criterio
        analise = resultado['resultado']
        
        # Verificar se foi aprovado
        foi_aprovado = "✅ APROVADO" in analise
        if foi_aprovado:
            aprovados += 1
        
        # Encontrar índice do critério na lista original
        criterio_index = None
        for idx, crit_original in enumerate(criterios_disponiveis):
            if crit_original['titulo'] == titulo:
                criterio_index = idx
                break
        
        # Definir valor padrão para próxima análise
        # Aprovados: desmarcados por padrão
        # Reprovados: marcados por padrão
        default_value = not foi_aprovado
        
        # Usar valor salvo se existir
        if criterio_index is not None:
            saved_value = st.session_state.proxima_analise_criterios.get(criterio_index, default_value)
        else:
            saved_value = default_value
        
        # Mostrar resultado com checkbox
        col1, col2 = st.columns([0.1, 0.9])
        
        with col1:
            if criterio_index is not None:
                checkbox_key = f"prox_analise_{criterio_index}"
                incluir_proxima = st.checkbox(
                    "",
                    value=saved_value,
                    key=checkbox_key,
                    help="Incluir na próxima análise"
                )
                st.session_state.proxima_analise_criterios[criterio_index] = incluir_proxima
        
        with col2:
            if foi_aprovado:
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
    
    # Seção para reanálise
    st.markdown("---")
    st.header("🔄 Nova Análise")
    st.markdown("**Dica:** Edite o roteiro acima e clique no botão abaixo para analisar novamente!")
    
    # Indicar se há critérios para próxima análise
    if 'proxima_analise_criterios' in st.session_state:
        criterios_marcados_prox = sum(1 for selecionado in st.session_state.proxima_analise_criterios.values() if selecionado)
        total_criterios_prox = len(st.session_state.proxima_analise_criterios)
        st.caption(f"📊 {criterios_marcados_prox}/{total_criterios_prox} critérios marcados para próxima análise")
        
        # Flag para indicar que deve reanalizar
        if st.button("🔄 Analisar Novamente", type="secondary", use_container_width=True, key="reanalise_resultados"):
            st.session_state.reanalizar = True
            st.rerun()
    else:
        st.info("ℹ️ Use os checkboxes acima para selecionar critérios e depois clique aqui para analisar novamente.")
    
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
            custo_usd = (total_tokens / 1000) * 0.015  # $0.015 por 1K tokens
        elif "gpt-4o-mini" in modelo_gpt:
            custo_usd = (total_tokens / 1000) * 0.0015  # $0.0015 por 1K tokens
        elif "gpt-4" in modelo_gpt:
            custo_usd = (total_tokens / 1000) * 0.03  # $0.03 por 1K tokens
        elif "gpt-3.5-turbo" in modelo_gpt:
            custo_usd = (total_tokens / 1000) * 0.002  # $0.002 por 1K tokens
        else:
            custo_usd = (total_tokens / 1000) * 0.01  # Estimativa genérica
        
        # Converter para reais (USD * 6)
        custo_brl = custo_usd * 6
        st.metric("Custo Estimado", f"R$ {custo_brl:.3f}")
    
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
        
        # Mostrar seleção de critérios apenas se não há resultados e não está analisando
        mostrar_criterios = (('ultimos_resultados' not in st.session_state or 
                           not st.session_state.ultimos_resultados) and
                           not st.session_state.get('analisando', False))
        
        if mostrar_criterios:
            # Seção de seleção de critérios
            st.markdown("---")
            st.header("📋 Critérios de Análise")
            st.markdown("**Selecione os critérios que deseja analisar:**")
            
            # Verificar se há critérios
            if not os.path.exists('criterios.txt'):
                st.error("❌ Arquivo criterios.txt não encontrado!")
                st.stop()
            
            # Carregar critérios
            try:
                criterios_disponiveis = carregar_criterios()
            except Exception as e:
                st.error(f"❌ Erro ao carregar critérios: {e}")
                st.stop()
            
            if not criterios_disponiveis:
                st.error("❌ Nenhum critério encontrado!")
                st.stop()
            
            # Inicializar estado dos critérios se não existir
            if 'criterios_selecionados' not in st.session_state:
                st.session_state.criterios_selecionados = {i: True for i in range(len(criterios_disponiveis))}
            
            # Mostrar critérios com checkboxes
            criterios_selecionados = {}
            for i, criterio in enumerate(criterios_disponiveis):
                titulo = criterio['titulo'] if isinstance(criterio, dict) else criterio
                descricao = criterio['descricao'] if isinstance(criterio, dict) else ""
                
                # Usar session_state para manter o estado
                key = f"criterio_{i}"
                default_value = st.session_state.criterios_selecionados.get(i, True)
                
                selecionado = st.checkbox(
                    titulo,
                    value=default_value,
                    key=key,
                    help=descricao if descricao else None
                )
                
                criterios_selecionados[i] = selecionado
            
            # Atualizar session_state
            st.session_state.criterios_selecionados = criterios_selecionados
            
            # Contar critérios selecionados
            total_criterios = len(criterios_disponiveis)
            criterios_marcados = sum(1 for selecionado in criterios_selecionados.values() if selecionado)
            
            st.caption(f"📊 {criterios_marcados}/{total_criterios} critérios selecionados")
            
            # Verificar se deve reanalizar (flag setado pelos resultados)
            deve_reanalizar = st.session_state.get('reanalizar', False)
            if deve_reanalizar:
                # Limpar flag
                st.session_state.reanalizar = False
                
                # Atualizar critérios com base na próxima análise
                if 'proxima_analise_criterios' in st.session_state:
                    st.session_state.criterios_selecionados = st.session_state.proxima_analise_criterios.copy()
                    criterios_selecionados = st.session_state.criterios_selecionados
                    criterios_marcados = sum(1 for selecionado in criterios_selecionados.values() if selecionado)
                
                if criterios_marcados > 0:
                    executar_analise_paralela(roteiro_content, modelo_gpt, criterios_selecionados, criterios_disponiveis)
            
            # Botões para analisar
            col1, col2 = st.columns(2)
            
            with col1:
                # Verificar se está analisando para desabilitar botão
                analisando = st.session_state.get('analisando', False)
                botao_text = "⏳ Analisando..." if analisando else "🔍 Analisar Roteiro"
                
                if st.button(botao_text, type="primary", use_container_width=True, disabled=analisando):
                    if criterios_marcados == 0:
                        st.error("❌ Selecione pelo menos um critério para análise!")
                    else:
                        # Marcar como analisando e recarregar página para ocultar critérios
                        st.session_state.analisando = True
                        st.rerun()
            
            with col2:
                # Mostrar botão de reanálise se já existem resultados
                if 'ultimos_resultados' in st.session_state and st.session_state.ultimos_resultados:
                    if st.button("🔄 Analisar Novamente", type="secondary", use_container_width=True, key="reanalise_topo"):
                        st.session_state.reanalizar = True
                        st.rerun()
                else:
                    st.empty()  # Manter layout consistente
        
        else:
            # Se há resultados, mostrar botão para nova análise com critérios diferentes
            st.markdown("---")
            if st.button("🔄 Nova Análise com Critérios Diferentes", type="secondary", use_container_width=True):
                # Limpar resultados e flag de análise para mostrar critérios novamente
                if 'ultimos_resultados' in st.session_state:
                    del st.session_state['ultimos_resultados']
                if 'analisando' in st.session_state:
                    del st.session_state['analisando']
                st.rerun()
            
            # Garantir que temos critérios disponíveis para mostrar
            try:
                criterios_disponiveis = carregar_criterios()
            except Exception as e:
                st.error(f"❌ Erro ao carregar critérios: {e}")
                criterios_disponiveis = []
        
        # Executar análise se o flag analisando estiver ativo
        if st.session_state.get('analisando', False):
            st.markdown("---")
            st.info("🚀 Iniciando análise...")
            
            # Garantir que temos os dados necessários
            if 'criterios_selecionados' in st.session_state:
                criterios_selecionados = st.session_state.criterios_selecionados
                criterios_marcados = sum(1 for selecionado in criterios_selecionados.values() if selecionado)
                
                if criterios_marcados > 0:
                    # Limpar flag de análise antes de executar
                    st.session_state.analisando = False
                    executar_analise_paralela(roteiro_content, modelo_gpt, criterios_selecionados, criterios_disponiveis)
                else:
                    # Se não há critérios selecionados, limpar flag
                    st.session_state.analisando = False
                    st.error("❌ Selecione pelo menos um critério para análise!")
            else:
                # Se não há critérios, limpar flag
                st.session_state.analisando = False
    
    else:
        st.warning("⚠️ Digite ou cole seu roteiro para começar a análise!")
    
    # Mostrar resultados salvos se existirem
    if 'ultimos_resultados' in st.session_state and st.session_state.ultimos_resultados:
        st.markdown("---")
        # Garantir que temos critérios disponíveis
        if not os.path.exists('criterios.txt'):
            st.error("❌ Arquivo criterios.txt não encontrado!")
        else:
            try:
                criterios_para_resultados = carregar_criterios()
                mostrar_resultados(
                    st.session_state.ultimos_resultados, 
                    st.session_state.ultimo_analisador, 
                    st.session_state.ultimo_modelo, 
                    criterios_para_resultados
                )
            except Exception as e:
                st.error(f"❌ Erro ao mostrar resultados: {e}")

if __name__ == "__main__":
    main()