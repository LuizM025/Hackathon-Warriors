# Bovinus MesaLimpa & SaborRadar

Unidade: Bovinus Grill & Beer — Rua Augusta (São Paulo/SP)
Equipe: Marcos Vinicius, Luiz Miguel e Victor Floriano
Foco: Almoço por peso (11h30 às 15h30 | ~600 executivos/dia | 90 mesas / 450 lugares em 3 praças)

- Vídeo da solução (até 2 min): [COLAR LINK AQUI]
- Apresentação (até 5 slides): [Hackathon Grupo Bovinus — Solução Integrada.pptx](https://github.com/user-attachments/files/35438898/Hackathon.Grupo.Bovinus.Solucao.Integrada.pptx)

---

## 1. Descrição do Problema & Solução Proposta

Na operação do almoço na Rua Augusta — especialmente no pico (12h10 às 13h20) — o Bovinus MesaLimpa & SaborRadar transforma eventos visuais já existentes no salão em métricas em tempo real, substituindo o "olhômetro" por decisões rápidas:

- Giro e limpeza das mesas: monitora o tempo de desocupação e limpeza nas 3 praças (Principal, Inferior e Superior, com 7 a 8 garçons), ajudando a liberar lugares mais rápido e evitar filas na escada da entrada com risco de desistência.
- Qualidade e sobras no prato: analisa a sobra nos pratos recolhidos na bancada antes do descarte para identificar rejeição por item do cardápio diário e orientar reposição/apresentação no buffet.
- Dentro e fora do escopo: 100% focado na jornada do salão, mantendo o atendimento humanizado (sem catracas) e sem alterar cozinha, compras, estoque ou o sistema de caixa/pagamentos (JS SoftCOM).
- Privacidade e viabilidade: reaproveita o CFTV Intelbras existente (por zonas de mesa, sem identificação facial/pessoal) + 1 câmera simples fixa com iluminação estável na bancada de retorno.

---

## 2. Detalhamento & Arquitetura em 3 Camadas

1. Camada 1 — Captura de Dados (Hardware Mínimo):
  - CFTV Intelbras existente monitora as 90 mesas nas 3 praças.
  - Câmera na bancada de retorno registra o prato recolhido antes do descarte.
2. Camada 2 — Inteligência & Processamento (motor-ia/):
  - MesaLimpa: classifica cada mesa em Livre, Ocupada ou Suja e dispara alerta se passar de 180 segundos (3 min) aguardando limpeza.
  - SaborRadar: segmentação visual (OpenCV) estima a área residual intacta por categoria do cardápio do dia e dispara alerta se a rejeição superar 20%.
3. Camada 3 — Visualização & Ação (painel-operacional/):
  - Dashboard web responsivo para gerente e maîtres com status das 3 praças, cronômetro de mesas críticas e ranking de rejeição do buffet.

---

## 3. Capturas de Tela da Solução

<img width="532" height="937" alt="fotosterminal (4)" src="https://github.com/user-attachments/assets/eb28722e-666f-412a-bf36-4f0b4edc1c66" />
<img width="1222" height="937" alt="fotosterminal (3)" src="https://github.com/user-attachments/assets/eef7f36f-92fc-4340-b4df-7065d5f3d722" />
<img width="846" height="511" alt="fotosterminal (2)" src="https://github.com/user-attachments/assets/ca773f8f-f4e9-4c71-97ba-3da0f0643fb7" />
<img width="912" height="963" alt="fotosterminal (1)" src="https://github.com/user-attachments/assets/c8f0e732-2c2c-4a71-a19e-33753b2602f4" />

---

## 4. Como Executar o Protótipo

### Painel Operacional (Web)
Abra o arquivo index diretamente em qualquer navegador moderno (Chrome, Edge, Firefox).

### Motor de IA (Python / OpenCV)
```bash
pip install opencv-python numpy
python motor-ia/mesalimpa_saborradar.py
