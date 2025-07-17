import os
import openai
import asyncio
from datetime import datetime

class AnalisadorRoteiro:
    def __init__(self, api_key=None, modelo="gpt-4o"):
        self._load_env()
        self.client = openai.OpenAI(
            api_key=api_key or os.getenv('OPENAI_API_KEY')
        )
        self.async_client = openai.AsyncOpenAI(
            api_key=api_key or os.getenv('OPENAI_API_KEY')
        )
        self.modelo = modelo
        self.log_requisicoes = []  # Log de todas as requisições
    
    def _load_env(self):
        """Carrega variáveis do arquivo .env"""
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read()
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
                        print(f"Carregado: {key.strip()}")  # Debug
        except FileNotFoundError:
            print("Arquivo .env não encontrado!")
        except Exception as e:
            print(f"Erro ao ler .env: {e}")
        
    def ler_criterios(self, arquivo_criterios='criterios.txt'):
        """Lê os critérios do arquivo TXT no formato: Título\nDescrição\n"""
        try:
            with open(arquivo_criterios, 'r', encoding='utf-8') as f:
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
            print(f"Arquivo {arquivo_criterios} não encontrado!")
            return []
    
    def ler_roteiro(self, arquivo_roteiro):
        """Lê o roteiro do arquivo"""
        try:
            with open(arquivo_roteiro, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Arquivo {arquivo_roteiro} não encontrado!")
            return None
    
    def _dividir_roteiro(self, roteiro, max_chars=8000):
        """Divide roteiro em partes menores se necessário"""
        if len(roteiro) <= max_chars:
            return [roteiro]
        
        partes = []
        palavras = roteiro.split()
        parte_atual = ""
        
        for palavra in palavras:
            if len(parte_atual + " " + palavra) > max_chars:
                if parte_atual:
                    partes.append(parte_atual.strip())
                parte_atual = palavra
            else:
                parte_atual += " " + palavra if parte_atual else palavra
        
        if parte_atual:
            partes.append(parte_atual.strip())
        
        return partes

    async def analisar_criterio_async(self, roteiro, criterio):
        """Analisa o roteiro com base em um critério específico usando ChatGPT (assíncrono)"""
        descricao = criterio['descricao'] if isinstance(criterio, dict) else criterio
        
        # Dividir roteiro se for muito grande
        partes_roteiro = self._dividir_roteiro(roteiro)
        
        if len(partes_roteiro) == 1:
            # Roteiro pequeno - análise normal
            return await self._analisar_parte_async(partes_roteiro[0], descricao)
        else:
            # Roteiro grande - analisar partes e consolidar
            print(f"  📝 Roteiro dividido em {len(partes_roteiro)} partes...")
            
            # Analisar todas as partes em paralelo
            tasks = []
            for i, parte in enumerate(partes_roteiro, 1):
                task = self._analisar_parte_async(parte, descricao, parte_num=i)
                tasks.append(task)
            
            print(f"    Analisando {len(tasks)} partes em paralelo...")
            analises_partes = await asyncio.gather(*tasks)
            
            # Consolidar análises
            return await self._consolidar_analises_async(analises_partes, descricao)

    def analisar_criterio(self, roteiro, criterio):
        """Analisa o roteiro com base em um critério específico usando ChatGPT"""
        descricao = criterio['descricao'] if isinstance(criterio, dict) else criterio
        
        # Dividir roteiro se for muito grande
        partes_roteiro = self._dividir_roteiro(roteiro)
        
        if len(partes_roteiro) == 1:
            # Roteiro pequeno - análise normal
            return self._analisar_parte(partes_roteiro[0], descricao)
        else:
            # Roteiro grande - analisar partes e consolidar
            print(f"  📝 Roteiro dividido em {len(partes_roteiro)} partes...")
            
            analises_partes = []
            for i, parte in enumerate(partes_roteiro, 1):
                print(f"    Analisando parte {i}/{len(partes_roteiro)}...")
                analise = self._analisar_parte(parte, descricao, parte_num=i)
                analises_partes.append(analise)
            
            # Consolidar análises
            return self._consolidar_analises(analises_partes, descricao)
    
    async def _analisar_parte_async(self, roteiro_parte, descricao, parte_num=None):
        """Analisa uma parte específica do roteiro (assíncrono)"""
        parte_info = f" (Parte {parte_num})" if parte_num else ""
        
        prompt = f"""
        Analise o seguinte roteiro com base no critério específico abaixo.
        
        CRITÉRIO A ANALISAR: {descricao}
        
        ROTEIRO:
        {roteiro_parte}
        
        INSTRUÇÕES IMPORTANTES:
        - Se o critério for TOTALMENTE ATENDIDO, responda APENAS: "✅ APROVADO"
        - NUNCA adicione explicações quando aprovado
        - Se houver problemas, forneça:
          1. "❌ NÃO ATENDE" ou "⚠️ ATENDE PARCIALMENTE"
          2. Explicação do problema
          3. Sugestões de melhoria
        
        Seja rigorosamente objetivo.
        """
        
        try:
            # Preparar dados da requisição
            messages = [
                {"role": "system", "content": "Você é um especialista em análise de roteiros de vídeo. Seja preciso e conciso."},
                {"role": "user", "content": prompt}
            ]
            
            # Fazer requisição assíncrona
            response = await self.async_client.chat.completions.create(
                model=self.modelo,
                messages=messages,
                max_tokens=500,
                temperature=0.1
            )
            
            # Extrair dados da resposta
            resposta_content = response.choices[0].message.content
            
            # Log da requisição
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "modelo": self.modelo,
                "tipo": "Análise de Critério (Async)",
                "prompt_chars": len(prompt),
                "resposta_chars": len(resposta_content),
                "tokens_input": response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                "tokens_output": response.usage.completion_tokens if hasattr(response, 'usage') else 0,
                "tokens_total": response.usage.total_tokens if hasattr(response, 'usage') else 0,
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "resposta": resposta_content
            }
            
            self.log_requisicoes.append(log_entry)
            
            return resposta_content
        except Exception as e:
            # Log do erro
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "modelo": self.modelo,
                "tipo": "ERRO (Async)",
                "erro": str(e),
                "prompt_chars": len(prompt),
                "resposta_chars": 0,
                "tokens_input": 0,
                "tokens_output": 0,
                "tokens_total": 0,
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "resposta": f"Erro: {str(e)}"
            }
            
            self.log_requisicoes.append(log_entry)
            
            return f"Erro na análise da parte: {str(e)}"

    def _analisar_parte(self, roteiro_parte, descricao, parte_num=None):
        """Analisa uma parte específica do roteiro"""
        parte_info = f" (Parte {parte_num})" if parte_num else ""
        
        prompt = f"""
        Analise o seguinte roteiro com base no critério específico abaixo.
        
        CRITÉRIO A ANALISAR: {descricao}
        
        ROTEIRO:
        {roteiro_parte}
        
        INSTRUÇÕES IMPORTANTES:
        - Se o critério for TOTALMENTE ATENDIDO, responda APENAS: "✅ APROVADO"
        - NUNCA adicione explicações quando aprovado
        - Se houver problemas, forneça:
          1. "❌ NÃO ATENDE" ou "⚠️ ATENDE PARCIALMENTE"
          2. Explicação do problema
          3. Sugestões de melhoria
        
        Seja rigorosamente objetivo.
        """
        
        try:
            # Preparar dados da requisição
            messages = [
                {"role": "system", "content": "Você é um especialista em análise de roteiros de vídeo. Seja preciso e conciso."},
                {"role": "user", "content": prompt}
            ]
            
            # Fazer requisição
            response = self.client.chat.completions.create(
                model=self.modelo,
                messages=messages,
                max_tokens=500,
                temperature=0.1
            )
            
            # Extrair dados da resposta
            resposta_content = response.choices[0].message.content
            
            # Log da requisição
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "modelo": self.modelo,
                "tipo": "Análise de Critério",
                "prompt_chars": len(prompt),
                "resposta_chars": len(resposta_content),
                "tokens_input": response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                "tokens_output": response.usage.completion_tokens if hasattr(response, 'usage') else 0,
                "tokens_total": response.usage.total_tokens if hasattr(response, 'usage') else 0,
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "resposta": resposta_content
            }
            
            self.log_requisicoes.append(log_entry)
            
            return resposta_content
        except Exception as e:
            # Log do erro
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "modelo": self.modelo,
                "tipo": "ERRO",
                "erro": str(e),
                "prompt_chars": len(prompt),
                "resposta_chars": 0,
                "tokens_input": 0,
                "tokens_output": 0,
                "tokens_total": 0,
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "resposta": f"Erro: {str(e)}"
            }
            
            self.log_requisicoes.append(log_entry)
            
            return f"Erro na análise da parte: {str(e)}"
    
    async def _consolidar_analises_async(self, analises_partes, descricao):
        """Consolida múltiplas análises em uma resposta final (assíncrono)"""
        analises_text = "\n\n".join([f"Parte {i+1}: {analise}" for i, analise in enumerate(analises_partes)])
        
        prompt = f"""
        Com base nas análises das partes do roteiro abaixo, forneça uma avaliação final:
        
        CRITÉRIO: {descricao}
        
        ANÁLISES DAS PARTES:
        {analises_text}
        
        INSTRUÇÕES:
        - Se TODAS as partes foram aprovadas, responda: "✅ APROVADO"
        - Se houver problemas em qualquer parte, forneça:
          1. Uma avaliação final (Não Atende/Parcialmente Atende)
          2. Resumo dos principais problemas encontrados
          3. Sugestões específicas de melhoria
        
        Seja objetivo e construtivo.
        """
        
        try:
            # Preparar dados da requisição
            messages = [
                {"role": "system", "content": "Você é um especialista em análise de roteiros de vídeo."},
                {"role": "user", "content": prompt}
            ]
            
            # Fazer requisição assíncrona
            response = await self.async_client.chat.completions.create(
                model=self.modelo,
                messages=messages,
                max_tokens=600,
                temperature=0.3
            )
            
            # Extrair dados da resposta
            resposta_content = response.choices[0].message.content
            
            # Log da requisição
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "modelo": self.modelo,
                "tipo": "Consolidação (Async)",
                "prompt_chars": len(prompt),
                "resposta_chars": len(resposta_content),
                "tokens_input": response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                "tokens_output": response.usage.completion_tokens if hasattr(response, 'usage') else 0,
                "tokens_total": response.usage.total_tokens if hasattr(response, 'usage') else 0,
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "resposta": resposta_content
            }
            
            self.log_requisicoes.append(log_entry)
            
            return resposta_content
        except Exception as e:
            # Log do erro
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "modelo": self.modelo,
                "tipo": "ERRO - Consolidação (Async)",
                "erro": str(e),
                "prompt_chars": len(prompt),
                "resposta_chars": 0,
                "tokens_input": 0,
                "tokens_output": 0,
                "tokens_total": 0,
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "resposta": f"Erro: {str(e)}"
            }
            
            self.log_requisicoes.append(log_entry)
            
            return f"Erro na consolidação: {str(e)}"

    def _consolidar_analises(self, analises_partes, descricao):
        """Consolida múltiplas análises em uma resposta final"""
        analises_text = "\n\n".join([f"Parte {i+1}: {analise}" for i, analise in enumerate(analises_partes)])
        
        prompt = f"""
        Com base nas análises das partes do roteiro abaixo, forneça uma avaliação final:
        
        CRITÉRIO: {descricao}
        
        ANÁLISES DAS PARTES:
        {analises_text}
        
        INSTRUÇÕES:
        - Se TODAS as partes foram aprovadas, responda: "✅ APROVADO"
        - Se houver problemas em qualquer parte, forneça:
          1. Uma avaliação final (Não Atende/Parcialmente Atende)
          2. Resumo dos principais problemas encontrados
          3. Sugestões específicas de melhoria
        
        Seja objetivo e construtivo.
        """
        
        try:
            # Preparar dados da requisição
            messages = [
                {"role": "system", "content": "Você é um especialista em análise de roteiros de vídeo."},
                {"role": "user", "content": prompt}
            ]
            
            # Fazer requisição
            response = self.client.chat.completions.create(
                model=self.modelo,
                messages=messages,
                max_tokens=600,
                temperature=0.3
            )
            
            # Extrair dados da resposta
            resposta_content = response.choices[0].message.content
            
            # Log da requisição
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "modelo": self.modelo,
                "tipo": "Consolidação",
                "prompt_chars": len(prompt),
                "resposta_chars": len(resposta_content),
                "tokens_input": response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                "tokens_output": response.usage.completion_tokens if hasattr(response, 'usage') else 0,
                "tokens_total": response.usage.total_tokens if hasattr(response, 'usage') else 0,
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "resposta": resposta_content
            }
            
            self.log_requisicoes.append(log_entry)
            
            return resposta_content
        except Exception as e:
            # Log do erro
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "modelo": self.modelo,
                "tipo": "ERRO - Consolidação",
                "erro": str(e),
                "prompt_chars": len(prompt),
                "resposta_chars": 0,
                "tokens_input": 0,
                "tokens_output": 0,
                "tokens_total": 0,
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "resposta": f"Erro: {str(e)}"
            }
            
            self.log_requisicoes.append(log_entry)
            
            return f"Erro na consolidação: {str(e)}"
    
    async def analisar_roteiro_completo_async(self, arquivo_roteiro, arquivo_criterios='criterios.txt'):
        """Analisa o roteiro completo com todos os critérios (assíncrono - paralelo)"""
        roteiro = self.ler_roteiro(arquivo_roteiro)
        if not roteiro:
            return None
            
        criterios = self.ler_criterios(arquivo_criterios)
        if not criterios:
            return None
        
        print(f"🚀 Iniciando análise paralela do roteiro com {len(criterios)} critérios...")
        
        # Criar tasks para análise paralela
        tasks = []
        for i, criterio in enumerate(criterios, 1):
            titulo = criterio['titulo'] if isinstance(criterio, dict) else criterio[:50]
            print(f"📋 Preparando análise do critério {i}/{len(criterios)}: {titulo}...")
            task = self.analisar_criterio_async(roteiro, criterio)
            tasks.append((criterio, task))
        
        # Executar todas as análises em paralelo
        print(f"⚡ Executando {len(tasks)} análises em paralelo...")
        resultados = []
        
        for criterio, task in tasks:
            resultado = await task
            resultados.append({
                'criterio': criterio,
                'resultado': resultado
            })
        
        print("✅ Análise paralela concluída!")
        return resultados

    def analisar_roteiro_completo(self, arquivo_roteiro, arquivo_criterios='criterios.txt'):
        """Analisa o roteiro completo com todos os critérios"""
        roteiro = self.ler_roteiro(arquivo_roteiro)
        if not roteiro:
            return None
            
        criterios = self.ler_criterios(arquivo_criterios)
        if not criterios:
            return None
        
        resultados = []
        
        print(f"Iniciando análise do roteiro com {len(criterios)} critérios...")
        
        for i, criterio in enumerate(criterios, 1):
            titulo = criterio['titulo'] if isinstance(criterio, dict) else criterio[:50]
            print(f"Analisando critério {i}/{len(criterios)}: {titulo}...")
            resultado = self.analisar_criterio(roteiro, criterio)
            resultados.append({
                'criterio': criterio,
                'resultado': resultado
            })
        
        return resultados
    
    def gerar_relatorio(self, resultados, arquivo_roteiro):
        """Gera um relatório final com todos os resultados"""
        if not resultados:
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"relatorio_analise_{timestamp}.txt"
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("RELATÓRIO DE ANÁLISE DE ROTEIRO\n")
            f.write("="*80 + "\n\n")
            f.write(f"Arquivo analisado: {arquivo_roteiro}\n")
            f.write(f"Data da análise: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Número de critérios analisados: {len(resultados)}\n\n")
            
            for i, resultado in enumerate(resultados, 1):
                criterio = resultado['criterio']
                titulo = criterio['titulo'] if isinstance(criterio, dict) else criterio
                
                f.write(f"CRITÉRIO {i}: {titulo}\n")
                f.write("-" * 40 + "\n")
                f.write("Análise:\n")
                f.write(resultado['resultado'])
                f.write("\n\n" + "="*80 + "\n\n")
        
        return nome_arquivo