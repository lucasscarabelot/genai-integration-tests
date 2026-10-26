# Análise Comparativa dos Prompts e Lições Aprendidas

Esta análise responde diretamente aos questionamentos propostos na atividade da Unidade III sobre o uso de GenAI como copiloto em testes de integração de software.

---

## 1. Como cada tipo de prompt influenciou a qualidade e a diversidade dos casos de teste?

| Dimensão de Comparação | Prompt Tipo 1 (Specification / Contract-Driven) | Prompt Tipo 2 (Adversarial / RBAC Boundary-Driven) |
| :--- | :--- | :--- |
| **Foco Primário** | Conformidade de schema OpenAPI/Pydantic, fluxo feliz e ciclo de vida linear da sessão. | Casos de abuso, quebra de autorização, integridade de tokens, replay attacks e auditoria transversal. |
| **Diversidade de Cenários** | **Média/Baixa.** Concentrou-se em validações estruturais de campos (ex: min_length, tipos) e fluxo sequencial básico (Login -> Refresh -> Logout). | **Alta.** Cobriu 8 vetores de falha distintos envolvendo múltiplos módulos integrados (Auth, Docs, Auditoria, Banco). |
| **Profundidade de Integração** | Testou a superfície da API (chamada HTTP -> resposta de schema). Pouca validação de efeitos colaterais de persistência. | Testou a integração profunda entre submódulos: se um 403 gerado pelo guardião RBAC realmente disparou um evento no submódulo de auditoria. |
| **Qualidade do Código Gerado** | Código direto e determinístico, muito próximo do modelo canônico de documentação. | Código sofisticado envolvendo manipulação de claims JWT em runtime, criação de assinaturas forjadas e asserções em coleções complexas. |
| **Vulnerabilidade a "Falsos Positivos"** | Baixa probabilidade de erro de execução, mas com falsa sensação de segurança por omitir brechas de integração. | Exigiu refino técnico mais apurado (como controle temporal e claims de token), mas revelou comportamentos reais de borda. |

---

## 2. Quais ajustes de prompt foram necessários para obter resultados mais úteis?

Ao experimentar os prompts com a LLM, foram identificados três problemas clássicos que exigiram ajustes estruturais (Prompt Engineering):

### A. Adicionar Restrições Explícitas de Arquitetura e Dependências
- **Problema Inicial:** A LLM gerou testes instanciando servidores assíncronos complexos com `requests` apontando para `http://localhost:8000`, o que exigiria subir uma instância real da aplicação em background.
- **Ajuste:** Especificou-se no prompt: *"Utilize pytest com TestClient do FastAPI de forma síncrona, consumindo fixtures organizadas em conftest.py"*. Isso eliminou a dependência de portas de rede e acelerou a execução para frações de segundo.

### B. Fornecer a Matriz de Acesso Explícita (Role-Based Access Control)
- **Problema Inicial:** Ao solicitar genericamente "testes de autorização", a LLM gerou apenas testes genéricos de "token inválido" ou testou apenas um único papel.
- **Ajuste:** No Prompt 2, foi injetada uma **tabela / matriz de papéis (Admin, Editor, Viewer)** com os verbos HTTP e permissões esperadas em cada rota. Isso permitiu que a LLM gerasse casos de escalonamento vertical (Viewer tentando criar doc) e horizontal (segregação de dados confidenciais).

### C. Exigir Detalhes Criptográficos e Asserções de Payload
- **Problema Inicial:** A LLM inicialmente verificava apenas `assert response.status_code == 401`, sem inspecionar o motivo do erro no JSON.
- **Ajuste:** O prompt foi instruído a validar o payload de erro (ex: `"Token revogado"`, `"Token expirado"`, `"Credenciais inválidas"`), garantindo que a falha ocorreu pelo motivo correto e não por um erro 401 genérico de rota não encontrada.

---

## 3. Reflexão: GenAI como "Copiloto" em Suítes de Integração

1. **A GenAI brilha na geração de volume e na exploração de casos adversariais:** Um engenheiro de software costuma ter viés de confirmação (testar o que foi programado para funcionar). Quando instruída com prompts adversariais, a LLM rapidamente sugere cenários que passariam despercebidos (como confusão entre Access e Refresh Token).
2. **A supervisão humana continua indispensável:** A IA não conhece detalhes sutis como a granularidade temporal de segundos em JWTs (`exp` e `iat`), o que pode fazer testes de rotação falharem se um identificador único (`jti`) não for planejado.
3. **Prompt Chaining / Abordagem Híbrida é o padrão ouro:** O melhor resultado é obtido usando o **Prompt 1** para garantir conformidade de contrato e pipeline CI/CD inicial, seguido pelo **Prompt 2** para estressar a segurança e a resiliência sistêmica da integração.
