# 🏛️ Terminal ICT: Institutional Order Flow & Macro Analytics

> ⚠️ **Status do Projeto: Em Desenvolvimento Ativo (WIP - Work in Progress)**
> O sistema está funcional em sua estrutura base de análise macro, com módulos de automação operacional e integração de múltiplos agentes de IA sendo implementados.

O **Terminal ICT** é uma plataforma de inteligência e análise de mercado baseada em conceitos de **Smart Money Concepts (SMC)** e **Inner Circle Trader (ICT)**. O sistema captura fluxos de dados e notícias de canais institucionais, processa as informações através de modelos de linguagem de última geração (LLMs) e fornece vieses direcionais (Daily Bias) e alertas operacionais de alta probabilidade.

---

## 🚀 Funcionalidades Atuais (Módulo Macro v2.0)

* **Sincronização de Fluxo de Dados:** Integração nativa com o `GNews` para varredura de dados macroeconômicos e sentimento de mercado (CFTC COT, DXY, Índices e Metais).
* **Análise de Viés Multi-Agente:** Processamento em tempo real dividindo a leitura em três pilares fundamentais através da API da **Groq (Llama 3.1)**:
    * **Institutional Flow:** Mapeamento de rastros de dinheiro institucional.
    * **Retail Trap:** Identificação de zonas de indução e armadilhas de varejo.
    * **Daily Bias:** Conclusão macro e viés direcional para o dia.
* **Interface Resiliente:** Construído em `Streamlit` com arquitetura de estado persistente (`st.session_state`) para evitar travamentos ou telas brancas durante o processamento pesado.

---

## 🗺️ Roadmap de Desenvolvimento (Próximos Passos)

- [x] Arquitetura base da interface e tratamento de cache.
- [x] Integração estável com API Groq Cloud.
- [ ] **Módulo de Gestão Estratégica:** Integração de agente especialista via **DeepSeek API**.
- [ ] **Módulo Operacional XAU/USD:** Implementação do algoritmo de **Numeração Psicológica (0-1-2-3-4-5)** focado na Kill Zone Asiática (23:20 e 01:15 PT).
- [ ] **Validação de Rejeição Automatizada:** Filtro de price action por varredura de pavios de candles de 5 minutos em níveis redondos estruturais.

---

## ⚙️ Pré-requisitos e Instalação

Para rodar o projeto localmente (via PyCharm/VS Code) ou preparar o deploy no Streamlit Cloud:

### 1. Dependências do Sistema
Certifique-se de que seu arquivo `requirements.txt` contém as bibliotecas necessárias:
```text
streamlit
groq
gnews
openai
