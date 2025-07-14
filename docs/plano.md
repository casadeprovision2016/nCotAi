# Plano de Projeto: COTAI - Sistema de Automação para Cotações e Editais

**Versão:** 1.0  
**Data:** 11 de julho de 2025

---

## 1. Introdução

O presente documento detalha o plano de desenvolvimento para o projeto COTAI, um sistema avançado de automação projetado para otimizar o gerenciamento de cotações e a participação em editais públicos e privados. A plataforma visa transformar processos comerciais e administrativos, empregando inteligência artificial para automatizar tarefas críticas como análise de editais, gestão de cotações e simulação de cenários de competitividade, proporcionando uma vantagem estratégica significativa para seus usuários.

## 2. Objetivos

### 2.1. Objetivo Principal
Desenvolver e implantar uma plataforma full-stack (Software as a Service - SaaS) robusta, escalável e intuitiva que automatize o ciclo de vida completo da participação em licitações.

### 2.2. Objetivos Específicos
- **Reduzir em 70%** o tempo operacional gasto na prospecção e análise de editais.
- Fornecer um sistema de **alertas inteligentes e proativos** para novas oportunidades de licitação alinhadas ao perfil do cliente.
- **Automatizar a extração de dados e cláusulas críticas** de documentos de editais (PDFs) utilizando OCR e Processamento de Linguagem Natural (PLN).
- Implementar um **dashboard centralizado** para visualização de métricas chave (KPIs), status de propostas e economia estimada.
- Oferecer ferramentas para **simulação de competitividade** e análise de cenários de cotação.
- Garantir a **segurança, integridade e confidencialidade** dos dados através de uma arquitetura de segurança em camadas.
- Desenvolver uma interface de usuário **intuitiva e acessível**, que reduza a curva de aprendizado e otimize a produtividade.

## 3. Metodologia

O projeto será executado utilizando uma metodologia de desenvolvimento ágil, com entregas incrementais e foco na qualidade e no feedback contínuo.

### 3.1. Stack Tecnológica
- **Backend:** Python (FastAPI), pela sua alta performance, produtividade e ecossistema robusto para IA.
- **Frontend:** React, por sua eficiência na criação de interfaces de usuário dinâmicas e componentizadas.
- **Serviços Especializados:** Go, para processamento concorrente de documentos PDF, garantindo máxima performance.
- **Banco de Dados:** PostgreSQL para dados relacionais e estruturados; MongoDB para dados não estruturados ou documentos (ex: resultados da análise de IA).
- **Mensageria e Tarefas Assíncronas:** Redis Streams e Celery para gerenciar tarefas de longa duração (ex: processamento de editais) de forma eficiente.

### 3.2. Arquitetura
A plataforma será construída sobre uma arquitetura de microsserviços híbrida e de alto desempenho, com comunicação segura via Service Mesh (Linkerd) e observabilidade unificada (OpenTelemetry, Prometheus, Jaeger).

### 3.3. Princípios de Design e Usabilidade
- **Padrão CRAP (Contraste, Repetição, Alinhamento, Proximidade):** Para garantir uma interface clara e consistente.
- **Acessibilidade (WCAG):** Conformidade para navegação por teclado, compatibilidade com leitores de tela e modos de alto contraste.
- **Performance:** Otimização focada em carregamento rápido (lazy loading), cache agressivo e uso de Web Workers.

## 4. Etapas ou Fases do Projeto

O desenvolvimento será segmentado nas seguintes fases:

### Fase 1: Fundação e Portal Web (Módulo 1)
- **Escopo:** Desenvolvimento do site institucional, landing page, blog e documentação. Captura de leads e apresentação do produto.
- **Entregáveis:** Site público com calculadora de ROI, estudos de caso e formulário para webinars.

### Fase 2: Autenticação e Segurança (Módulo 2)
- **Escopo:** Implementação do sistema de gerenciamento de usuários, incluindo login, registro, MFA, SSO (Gov.br) e controle de acesso baseado em função (RBAC).
- **Entregáveis:** Módulo de autenticação seguro com cookies `HttpOnly`, tokens rotativos e auditoria de acessos.

### Fase 3: Dashboard e Funcionalidades Core - Especificação Detalhada

#### 3.1. Estrutura Principal da Interface

##### 3.1.1. Layout e Arquitetura de Componentes
- **Sistema de Grid Responsivo:**
  - Container principal com CSS Grid de 12 colunas
  - Breakpoints: Mobile (< 768px), Tablet (768px - 1024px), Desktop (> 1024px)
  - Sistema de layout adaptativo com redistribuição automática de componentes
  
- **Estrutura de Componentes:**
  ```
  AppLayout
  ├── HeadBar (fixo no topo)
  ├── SideBar (colapsável)
  ├── MainContent (scrollável)
  └── GlobalModals (notificações, confirmações)
  ```

##### 3.1.2. HeadBar Detalhado
- **Componentes da Esquerda para Direita:**
  - **Logo/Branding:** Com animação de hover e link para home
  - **Breadcrumbs Dinâmicos:** Navegação contextual com histórico
  - **Busca Global:** 
    - Pesquisa unificada com sugestões em tempo real
    - Shortcuts de teclado (Ctrl+K)
    - Histórico de buscas recentes
  
- **Seletor de Tema Avançado:**
  - Modo Claro/Escuro/Automático (segue sistema)
  - Temas customizáveis com paleta de cores
  - Transições suaves entre temas (300ms)
  - Persistência em `localStorage` com fallback para preferências do sistema
  
- **Sistema de Notificações:**
  - **Badge com Contador Animado:** Exibe total não lido
  - **Dropdown de Notificações:**
    - Agrupamento por categoria (Licitações, Tarefas, Sistema, Mensagens)
    - Preview com título, descrição e timestamp relativo
    - Ações rápidas: Marcar como lida, arquivar, responder
    - Link "Ver todas" para página dedicada
  - **Configurações de Notificação:**
    - Toggle por categoria
    - Horário de não perturbar
    - Sons personalizáveis
  
- **Menu de Perfil Expandido:**
  - **Informações Visíveis:**
    - Avatar com indicador de status online/ausente
    - Nome completo e cargo
    - Empresa/departamento
  - **Menu Dropdown:**
    - Meu Perfil (com preview de completude)
    - Configurações da Conta
    - Preferências de Notificação
    - Atalhos de Teclado
    - Central de Ajuda
    - Logout com confirmação

##### 3.1.3. SideBar Aprimorada
- **Estrutura Hierárquica:**
  - **Módulos Principais:** Ícones grandes com labels
  - **Submódulos:** Expansíveis com animação
  - **Favoritos:** Seção customizável pelo usuário
  
- **Funcionalidades:**
  - **Modo Compacto/Expandido:** Toggle com memória de preferência
  - **Indicadores Visuais:**
    - Badges de contagem em módulos (ex: "3 novas licitações")
    - Highlight do módulo ativo
    - Tooltips em modo compacto
  - **Busca Interna:** Campo de filtro rápido de módulos
  - **Rodapé da Sidebar:**
    - Versão do sistema
    - Status da conexão
    - Link para changelog

#### 3.2. Módulo de Início (Home) Expandido

##### 3.2.1. Dashboard Analítico
- **Grid de KPIs Dinâmicos:**
  - **Cards Primários (sempre visíveis):**
    - Economia Total Realizada (com gráfico sparkline)
    - Taxa de Sucesso em Licitações (com comparativo mensal)
    - Editais em Andamento (separados por fase)
    - Alertas Críticos (vencimentos próximos)
  
  - **Cards Secundários (customizáveis):**
    - Volume de Propostas por Mês
    - Tempo Médio de Resposta
    - Performance da Equipe
    - Próximos Marcos Importantes

##### 3.2.2. Visualizações de Dados
- **Gráfico de Editais por Status:**
  - Tipo: Donut Chart interativo com drill-down
  - Legendas clicáveis para filtrar
  - Animações de entrada e transição
  - Export para PNG/SVG
  
- **Heatmap de Atividade:**
  - Visualização estilo GitHub contribution graph
  - Período: Últimos 12 meses com zoom semanal
  - Tooltips detalhados por dia
  - Métricas: Editais criados, propostas enviadas, tarefas concluídas
  
- **Timeline de Eventos:**
  - Linha do tempo horizontal scrollável
  - Eventos: Vencimentos, reuniões, marcos de projeto
  - Filtros por tipo e urgência

##### 3.2.3. Widgets Personalizáveis
- **Sistema de Drag & Drop:**
  - Reorganização livre de componentes
  - Redimensionamento de widgets (S/M/L)
  - Salvamento de layouts personalizados
  
- **Biblioteca de Widgets:**
  - Calendário com eventos
  - Feed de atividades recentes
  - Lista de tarefas prioritárias
  - Relatório de economia mensal
  - Ranking de fornecedores

#### 3.3. Módulo nLic (Futuras Licitações) Avançado

##### 3.3.1. Motor de Busca Inteligente
- **Processamento de Linguagem Natural:**
  - Interpretação de queries complexas
  - Sugestões de sinônimos e termos relacionados
  - Correção ortográfica automática
  
- **Filtros Avançados:**
  - **Por Categoria:**
    - Tipo de licitação (Pregão, Concorrência, etc.)
    - Modalidade (Eletrônico, Presencial)
    - Categoria de produto/serviço (com taxonomia)
  - **Por Critérios:**
    - Faixa de valor (com slider duplo)
    - Localização (com mapa interativo)
    - Órgãos específicos (com autocomplete)
    - Data de publicação e vencimento
    - Tipo de garantia exigida
  - **Filtros Salvos:** Criação de "Buscas Inteligentes" reutilizáveis

##### 3.3.2. Sistema de Scoring e Relevância
- **Algoritmo de Pontuação:**
  - Match de palavras-chave (40%)
  - Histórico de sucesso em órgão similar (20%)
  - Adequação ao perfil da empresa (20%)
  - Prazo disponível (10%)
  - Valor estimado vs capacidade (10%)
  
- **Indicadores Visuais:**
  - Score de 0-100 com código de cores
  - Tags de "Alta Relevância", "Nova Oportunidade"
  - Ícones de urgência para prazos curtos

##### 3.3.3. Alertas e Automações
- **Configuração de Alertas:**
  - **Triggers Personalizáveis:**
    - Nova licitação matching critérios
    - Alteração em edital monitorado
    - Aproximação de deadline
  - **Canais de Notificação:**
    - In-app com som customizável
    - Email com template rico
    - SMS para alertas críticos
    - Integração com WhatsApp Business
    - Webhooks para sistemas externos
  
- **Relatórios Automatizados:**
  - **Daily Digest:** Resumo matinal de novas oportunidades
  - **Weekly Report:** Análise de tendências e oportunidades perdidas
  - **Formato:** HTML responsivo, PDF anexo opcional

#### 3.4. Módulo CotAi (Sistema Kanban) Completo

##### 3.4.1. Board Kanban Avançado
- **Estrutura de Colunas:**
  1. **Backlog:** Oportunidades identificadas
  2. **Cadastro:** Em processo de registro
  3. **Análise:** Processamento IA/OCR
  4. **Cotação:** Formação de preço
  5. **Revisão:** Checagem final
  6. **Proposta:** Preparação do envio
  7. **Enviado:** Aguardando resultado
  8. **Finalizado:** Ganho/Perdido/Cancelado

- **Funcionalidades do Board:**
  - **Swimlanes:** Agrupamento por órgão, valor ou prioridade
  - **WIP Limits:** Limite de trabalho em progresso por coluna
  - **Card Aging:** Indicador visual para cards parados
  - **Quick Actions:** Ações rápidas no hover do card

##### 3.4.2. Processamento Inteligente
- **OCR e Extração de Dados:**
  - **Upload Múltiplo:** Drag & drop de múltiplos PDFs
  - **Pré-processamento:** Otimização de imagem, correção de rotação
  - **Extração Estruturada:**
    - Dados do órgão comprador
    - Itens e quantidades
    - Requisitos técnicos
    - Prazos e condições
    - Cláusulas especiais
  
- **Análise por IA:**
  - **Identificação de Riscos:**
    - Cláusulas prejudiciais destacadas
    - Requisitos impossíveis de cumprir
    - Penalidades desproporcionais
  - **Sugestões Automáticas:**
    - Fornecedores recomendados
    - Histórico de preços similares
    - Checklist de documentação

##### 3.4.3. Módulo de Cotação
- **Simulador de Cenários:**
  - **Variáveis Configuráveis:**
    - Custos diretos e indiretos
    - Margem de lucro desejada
    - Impostos e taxas
    - Risco do projeto
  - **Análise What-If:** Múltiplos cenários side-by-side
  - **Gráficos de Break-Even:** Ponto de equilíbrio visual
  
- **Inteligência Competitiva:**
  - Base histórica de preços vencedores
  - Análise de competidores frequentes
  - Sugestão de preço ótimo com IA

##### 3.4.4. Geração de Documentos
- **Templates Inteligentes:**
  - Biblioteca de modelos por tipo de licitação
  - Preenchimento automático com dados extraídos
  - Versionamento de propostas
  
- **Exportação Avançada:**
  - **Formatos:** PDF, Word, Excel
  - **Personalização:** Cabeçalhos, logos, assinaturas
  - **Pacote Completo:** ZIP com todos documentos necessários

#### 3.5. Módulo de Mensagens Colaborativo

##### 3.5.1. Sistema de Chat Contextual
- **Estrutura de Conversas:**
  - **Threads por Contexto:**
    - Vinculadas a editais específicos
    - Associadas a tarefas
    - Discussões gerais por tópico
  - **Metadados Visíveis:**
    - Participantes ativos
    - Arquivos compartilhados
    - Decisões tomadas (pinned messages)

##### 3.5.2. Funcionalidades de Comunicação
- **Editor Rico:**
  - Formatação (negrito, itálico, listas)
  - Code snippets com syntax highlighting
  - Tabelas editáveis inline
  - Emojis e reações
  
- **Menções e Notificações:**
  - @todos, @aqui para notificações em massa
  - @usuário com autocomplete
  - Notificações desktop/mobile configuráveis
  
- **Compartilhamento:**
  - Upload de arquivos com preview
  - Integração com Google Drive/Dropbox
  - Compartilhamento de tela para reuniões rápidas

##### 3.5.3. Templates e Automações
- **Biblioteca de Templates:**
  - Solicitação de cotação
  - Aprovação de proposta
  - Checklist de documentos
  - Comunicados padrão
  
- **Respostas Automáticas:**
  - Confirmação de recebimento
  - Redirecionamento em ausência
  - FAQ bot para dúvidas comuns

#### 3.6. Módulo de Tarefas Inteligente

##### 3.6.1. Matriz de Eisenhower Interativa
- **Quadrantes Visuais:**
  1. **Urgente & Importante:** Cor vermelha, fazer agora
  2. **Importante & Não Urgente:** Cor azul, planejar
  3. **Urgente & Não Importante:** Cor amarela, delegar
  4. **Nem Urgente Nem Importante:** Cor cinza, eliminar
  
- **Funcionalidades:**
  - Drag & drop entre quadrantes
  - Sugestões automáticas de classificação
  - Análise de tempo gasto por quadrante

##### 3.6.2. Sistema de Tarefas Avançado
- **Criação de Tarefas:**
  - **Campos Detalhados:**
    - Título e descrição rica
    - Estimativa de tempo (com timer Pomodoro)
    - Dependências entre tarefas
    - Subtarefas com progress tracking
    - Anexos e links relacionados
  
- **Atribuição Inteligente:**
  - Análise de carga de trabalho em tempo real
  - Sugestão baseada em skills e disponibilidade
  - Balanceamento automático de equipe
  - Notificação de sobrecarga

##### 3.6.3. Automações e Integrações
- **Tarefas Recorrentes:**
  - Configuração flexível (diária, semanal, mensal, customizada)
  - Templates para tarefas recorrentes
  - Ajuste automático para dias úteis
  
- **Integrações Externas:**
  - Sincronização com Google Calendar
  - Export para Microsoft Project
  - Webhooks para ferramentas de CI/CD
  - API REST para integrações customizadas

#### 3.7. Funcionalidades Transversais

##### 3.7.1. Sistema de Permissões Granular
- **Níveis de Acesso:**
  - Super Admin: Acesso total
  - Admin: Gestão de usuários e configurações
  - Gerente: Acesso a relatórios e aprovações
  - Operador: Execução de tarefas
  - Visualizador: Apenas leitura
  
- **Permissões por Recurso:**
  - CRUD individual por módulo
  - Restrições por valor de licitação
  - Acesso temporal (para consultores)

##### 3.7.2. Auditoria e Compliance
- **Log de Atividades:**
  - Registro completo de ações
  - Filtros por usuário, data, tipo
  - Export para análise forense
  
- **Conformidade:**
  - Assinatura digital de documentos
  - Trilha de auditoria imutável
  - Backup automático com retenção configurável

##### 3.7.3. Performance e Otimização
- **Cache Inteligente:**
  - Redis para dados frequentes
  - Service Workers para offline
  - Lazy loading de componentes
  
- **Monitoramento:**
  - Dashboard de performance em tempo real
  - Alertas de degradação
  - Análise de uso por feature

### Fase 4: Escalabilidade e Inteligência Avançada
- **Escopo:** Otimização de performance com componentes em Go, refino dos modelos de IA e introdução de módulos de segurança avançados (Rust).
- **Entregáveis:** Pipelines de processamento de documentos otimizados e modelos de IA com maior acurácia.

## 5. Recursos Necessários

### 5.1. Equipe (Pessoal)
- Gerente de Projeto
- Arquiteto de Software
- Desenvolvedor Backend (Python, Go)
- Desenvolvedor Frontend (React)
- Engenheiro de DevOps/SRE
- Especialista em IA/ML
- Analista de QA

### 5.2. Software e Ferramentas
- **Controle de Versão:** Git (GitHub/GitLab).
- **Gestão de Projeto:** Jira, Trello ou similar.
- **CI/CD:** Jenkins, GitLab CI ou GitHub Actions.
- **Infraestrutura:** Plataforma de nuvem (AWS, GCP ou Azure), Docker, Kubernetes.

## 6. Cronograma (Estimativa de Alto Nível)

- **Fase 1:** 4-6 semanas
- **Fase 2:** 3-4 semanas
- **Fase 3:** 8-10 semanas
- **Fase 4:** Desenvolvimento contínuo (pós-lançamento do MVP)

## 7. Responsabilidades

- **Gerente de Projeto:** Supervisão geral, gestão de stakeholders e cronograma.
- **Arquiteto de Software:** Tomada de decisões técnicas, garantia de qualidade e padrões de código.
- **Equipe de Desenvolvimento (Frontend/Backend/IA):** Implementação das funcionalidades conforme as especificações.
- **Engenheiro de DevOps:** Automação da infraestrutura, implantação e monitoramento.
- **Analista de QA:** Planejamento e execução de testes para garantir a qualidade do produto.

## 8. Indicadores de Sucesso (KPIs)

O sucesso do projeto será medido pelos seguintes indicadores:
- **KPI de Performance:** Redução de 40% no tempo de operações diárias dos usuários.
- **KPI de Negócio:** Aumento no número de licitações vencidas pelos clientes.
- **KPI de Produto:** Taxa de adoção das funcionalidades de automação e IA > 80%.
- **KPI de Qualidade:** Uptime do sistema > 99.9%; Baixo volume de bugs críticos em produção.
- **KPI de Satisfação:** Net Promoter Score (NPS) > 50.

## 9. Referências

- Documento Fonte: `CotAi.md - Plano Completo de Desenvolvimento Full-Stack`.
