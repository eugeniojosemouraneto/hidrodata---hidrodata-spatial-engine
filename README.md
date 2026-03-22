# 💧 HidroData - Motor Geoespacial e Ingestão de Dados

## 📌 Sobre o Projeto
Este repositório contém a **Fase 1 (Infraestrutura Espacial)** do projeto HidroData, desenvolvido no âmbito de uma Iniciação Científica. O objetivo principal do sistema é atuar como um orquestrador de Big Data espacial, coletando, limpando e cruzando dados pluviométricos (ANA) e meteorológicos (INMET) com variáveis topográficas de alta precisão.

O sistema foca na mitigação de problemas de I/O Bound e CPU Bound através de arquitetura assíncrona, visando preparar tensores de dados limpos para futuras predições com Redes Neurais.

## 🛠️ Tecnologias Utilizadas
- **Linguagem:** Python 3.12
- **Framework Web:** Django 6.0.3
- **Banco de Dados:** PostgreSQL + PostGIS (Geoprocessamento)
- **Assincronismo:** Celery + Redis (Fila de Mensagens)
- **Engenharia de Dados:** Pandas, Hydrobr, Numpy, Pydantic
- **Infraestrutura:** Docker & Docker Compose

---

## 📖 Histórico de Implementação (Commits) e Fundamentação Científica

Abaixo estão detalhadas as etapas de desenvolvimento, justificando as escolhas arquiteturais e a teoria científica aplicada em cada bloco.

### 📍 Etapa 1: Infraestrutura e Configuração Base
- **Teoria da Programação:** Configuração de um ambiente conteinerizado (Docker) para garantir a reprodutibilidade da pesquisa. Implementação do Django com arquitetura de filas (Celery/Redis).
- **Justificativa (Tema):** A modelagem hidrológica exige processamento pesado contínuo. Isolar a aplicação web dos *workers* de background evita travamentos e permite que a raspagem de dados ocorra em lote sem afetar o usuário final.

### 📍 Etapa 2: Modelagem de Dados Espaciais (PostGIS)
- **Teoria da Programação:** Estruturação das entidades `Station` e `RawPrecipitation` com uso do `PointField` do PostGIS (SRID 4326) e Índices BRIN (`BrinIndex`) para datas.
- **Justificativa (Tema):** Séries temporais meteorológicas geram milhões de linhas rapidamente. O índice BRIN agrupa dados sequenciais por blocos físicos no disco, reduzindo o tempo de leitura no PostGIS. A tipagem espacial (`Point`) permite cálculos trigonométricos direto na base.

### 📍 Etapa 3: Sincronização de Metadados via API (ANA/INMET)
- **Teoria da Programação:** Uso de Teoria de Conjuntos matemáticos (`set` e `.intersection()`) em Python para calcular o *Delta* (diferença) entre a malha de estações da API e a do Banco de Dados.
- **Justificativa (Tema):** Reduz a complexidade de tempo de $O(N^2)$ para $O(N)$ ao orquestrar atualizações, desativações e novas estações (mais de 22 mil alvos), poupando RAM e processamento do servidor durante o *Crawling*.

### 📍 Etapa 4: Enriquecimento Altimétrico (OpenTopoData)
- **Teoria da Programação:** Consumo assíncrono em lote (*Batch Request*) com tratamento de *Rate Limit* e tolerância a falhas (*Retry* Exponencial no Celery).
- **Justificativa (Tema):** A variável $Z$ (altitude) é crucial para entender chuvas orográficas. O empacotamento de 50 coordenadas por requisição protege o *pipeline* de bloqueios (Erro 429) por parte da API pública de radares de satélite.

### 📍 Etapa 5: Motor Geoespacial e Busca por Quadrantes
- **Teoria da Programação:** Uso da função `.annotate()` do Django ORM interagindo com C/C++ nativo do PostGIS para calcular `Distance` e `Azimuth`. Fatiamento matricial (NE, NW, SE, SW).
- **Justificativa (Tema):** Algoritmos preditivos (como IDW e Advecção) sofrem de erro espacial (viés direcional) se todas as referências estiverem no mesmo lado. A busca radial forçada por quadrantes garante que o "Alvo" seja circundado por estações em 360 graus.

### 📍 Etapa 6: Interface de Análise Espacial (UI)
- **Teoria da Programação:** *Server-Side Rendering* (SSR) limpo, acoplado à biblioteca Leaflet para mapas. Uso de injeção CSS nativa para rotação vetorial de azimute, dispensando *frameworks* pesados no front-end.
- **Justificativa (Tema):** Fornece aos pesquisadores uma plataforma visual imediata para validação do "Delta H" (diferença orográfica) e geometria de distâncias, acelerando a fase de checagem dos tensores de dados.