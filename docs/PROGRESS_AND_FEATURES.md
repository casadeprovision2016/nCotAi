# Visão Geral do Projeto COTAI: Funcionalidades e Componentes Implementados

**Versão:** 1.0  
**Data de Extração:** 11 de julho de 2025  
**Fonte:** `plano.md`

---

Este documento descreve a arquitetura de funcionalidades e os componentes detalhados do sistema COTAI, conforme especificado na Fase 3 do plano de projeto. Ele representa a base de funcionalidades implementadas e em desenvolvimento ativo.

## 1. Estrutura Principal da Interface (Core UI)

A interface do sistema é projetada para ser moderna, responsiva e intuitiva, baseada em uma arquitetura de componentes robusta.

### 1.1. Layout e Arquitetura de Componentes
- **Grid Responsivo:** Utiliza um sistema de 12 colunas (CSS Grid) que se adapta a diferentes tamanhos de tela (Mobile, Tablet, Desktop).
- **Layout Principal (`AppLayout`):**
  - `HeadBar`: Barra superior fixa.
  - `SideBar`: Menu lateral colapsável.
  - `MainContent`: Área de conteúdo principal com scroll.
  - `GlobalModals`: Camada para notificações e diálogos globais.

### 1.2. HeadBar (Barra Superior)
- **Navegação e Identidade:**
  - **Logo/Branding:** Identidade visual com link para a página inicial.
  - **Breadcrumbs Dinâmicos:** Exibem o caminho de navegação atual.
- **Busca Global:** Ferramenta de pesquisa unificada com sugestões em tempo real e atalho de teclado (Ctrl+K).
- **Seletor de Tema Avançado:** Permite alternar entre os modos Claro, Escuro e Automático, com persistência da escolha.
- **Sistema de Notificações:**
  - **Badge com Contador:** Indica o número de notificações não lidas.
  - **Dropdown Detalhado:** Agrupa notificações por categoria (Licitações, Tarefas, etc.) e permite ações rápidas (marcar como lida, arquivar).
  - **Configurações:** Permite ao usuário personalizar quais notificações deseja receber e como.
- **Menu de Perfil Expandido:** Exibe informações do usuário (avatar, nome, cargo) e oferece acesso a configurações, central de ajuda e logout.

### 1.3. SideBar (Menu Lateral)
- **Estrutura Hierárquica:** Organiza o acesso aos módulos principais e submódulos expansíveis.
- **Funcionalidades:**
  - **Modo Compacto/Expandido:** Permite ao usuário otimizar o espaço de tela.
  - **Indicadores Visuais:** Badges de contagem (ex: "3 novas licitações") e destaque do módulo ativo.
  - **Busca Rápida:** Filtro para encontrar módulos facilmente.

## 2. Módulo de Início (Dashboard Analítico)

O dashboard centraliza as informações mais críticas para o usuário.

### 2.1. Grid de KPIs Dinâmicos
- **Cards Principais:** Exibem métricas essenciais como "Economia Total Realizada", "Taxa de Sucesso" e "Editais em Andamento".
- **Cards Secundários:** Widgets customizáveis para métricas como "Volume de Propostas" e "Performance da Equipe".

### 2.2. Visualizações de Dados
- **Gráfico de Editais por Status:** Donut chart interativo para análise rápida do funil de licitações.
- **Heatmap de Atividade:** Visualização de contribuições (estilo GitHub) para monitorar a atividade ao longo do tempo.
- **Timeline de Eventos:** Linha do tempo horizontal para visualizar prazos, reuniões e marcos importantes.

### 2.3. Widgets Personalizáveis
- **Layout Flexível:** Sistema de Drag & Drop para reorganizar e redimensionar widgets.
- **Biblioteca de Widgets:** Inclui calendário, feed de atividades, lista de tarefas, entre outros.

## 3. Módulo nLic (Busca de Licitações)

Motor de busca avançado para prospecção de novas oportunidades.

### 3.1. Busca Inteligente
- **Processamento de Linguagem Natural (PLN):** Interpreta buscas complexas e corrige erros ortográficos.
- **Filtros Avançados:** Permite filtrar por tipo de licitação, valor, localização, órgão, datas e salvar buscas para reuso.

### 3.2. Sistema de Scoring e Relevância
- **Algoritmo de Pontuação:** Classifica as oportunidades com base em palavras-chave, histórico de sucesso e adequação ao perfil da empresa.
- **Indicadores Visuais:** Exibe um score de 0-100 e tags como "Alta Relevância" para facilitar a identificação.

### 3.3. Alertas e Automações
- **Alertas Personalizáveis:** Notificam sobre novas licitações, alterações em editais e prazos próximos.
- **Canais de Notificação:** In-app, Email, SMS e Webhooks.
- **Relatórios Automatizados:** Envio de resumos diários e semanais de oportunidades.

## 4. Módulo CotAi (Gestão de Propostas - Kanban)

Sistema visual para gerenciar o ciclo de vida das cotações e propostas.

### 4.1. Board Kanban Avançado
- **Colunas de Fluxo:** Estrutura visual desde o "Backlog" até "Finalizado" (Ganho/Perdido).
- **Funcionalidades:** Suporta Swimlanes (agrupamento por prioridade), WIP Limits e indicadores de "envelhecimento" dos cards.

### 4.2. Processamento Inteligente de Documentos
- **OCR e Extração de Dados:** Extrai informações estruturadas de editais em PDF, como itens, prazos e requisitos.
- **Análise por IA:**
  - **Identificação de Riscos:** Destaca cláusulas prejudiciais e requisitos de difícil cumprimento.
  - **Sugestões Automáticas:** Recomenda fornecedores, histórico de preços e checklists de documentos.

### 4.3. Módulo de Cotação e Simulação
- **Simulador de Cenários:** Ferramenta para análise "What-If", permitindo configurar custos, margens e impostos para simular diferentes cenários de preço.
- **Inteligência Competitiva:** Analisa o histórico de preços de vencedores e concorrentes para sugerir o preço ótimo.

### 4.4. Geração de Documentos
- **Templates Inteligentes:** Preenche automaticamente modelos de propostas com os dados extraídos.
- **Exportação Avançada:** Gera pacotes completos (ZIP) com todos os documentos necessários em formatos como PDF e Word.

## 5. Módulos Colaborativos

### 5.1. Módulo de Mensagens
- **Chat Contextual:** Permite criar conversas (threads) vinculadas a editais ou tarefas específicas.
- **Funcionalidades Ricas:** Suporta formatação de texto, menções, reações, compartilhamento de arquivos e templates de mensagens.

### 5.2. Módulo de Tarefas Inteligente
- **Matriz de Eisenhower Interativa:** Ajuda a priorizar tarefas com base na urgência e importância.
- **Sistema de Tarefas Avançado:** Permite criar tarefas com subtarefas, dependências, estimativas de tempo e atribuição inteligente baseada na carga de trabalho da equipe.

## 6. Funcionalidades Transversais

- **Sistema de Permissões Granular:** Controle de acesso detalhado por função (RBAC) e por recurso.
- **Auditoria e Compliance:** Log completo de atividades e trilha de auditoria imutável para garantir a conformidade.
- **Performance e Otimização:** Arquitetura focada em performance com cache inteligente, lazy loading e monitoramento em tempo real.
