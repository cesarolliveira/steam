# 🚀 STEAM

## 📌 Pré-requisitos

Certifique-se de que os seguintes pacotes estão instalados:

- [x] Make
- [x] Git
- [x] Bash-completion
- [x] K3s
- [x] Helm

## 🌍 Configuração do Traefik

Para editar o serviço do Traefik e adicionar a porta de administração:

```bash
kubectl edit svc traefik -n kube-system
```

Adicione a seguinte configuração:

```yaml
- name: traefik
  port: 9000
  protocol: TCP
  targetPort: 9000
```

---

## 🐇 Instalação do RabbitMQ

Adicionar o repositório Helm do RabbitMQ:

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

Instalar o RabbitMQ:

```bash
helm upgrade --install --create-namespace --namespace steam rabbitmq bitnami/rabbitmq \
  --version 15.0.6 -f resources/rabbitmq/values.yaml
```

### 🔑 Configuração do usuário

```bash
# Adicionar tag de administrador ao usuário
kubectl exec -it rabbitmq-0 -n steam -- rabbitmqctl set_user_tags user administrator

# Conceder permissões ao usuário
kubectl exec -it rabbitmq-0 -n steam -- rabbitmqctl set_permissions -p / user ".*" ".*" ".*"

# Alterar a senha do usuário
kubectl exec -it rabbitmq-0 -n steam -- rabbitmqctl change_password user steam@2025

# Autenticar usuário
kubectl exec -it rabbitmq-0 -n steam -- rabbitmqctl authenticate_user user steam@2025
```

### 🗑️ Remover todas as filas do RabbitMQ

```bash
kubectl exec -it -n steam rabbitmq-0 -- sh -c "rabbitmqctl list_queues | grep -v Listing | awk 'NR>2 {print \$1}' | xargs -I{} rabbitmqctl delete_queue {}"
```

---

## ⚙️ Iniciando os serviços

### 🏭 Producer

Iniciar o **Producer**:

```bash
make start-producer
```

Parar o **Producer**:

```bash
make stop-producer
```

Logs do **Producer**:

```bash
kubectl logs -n steam -l app=producer -f
```

### 🏗️ Consumer

Iniciar o **Consumer**:

```bash
# Para VPS
make start-consumer environment=vps

# Para Raspberry Pi
make start-consumer environment=rasp-berry
```

Parar o **Consumer**:

```bash
make stop-consumer
```

Logs do **Consumer**:

```bash
kubectl logs -n steam -l app.kubernetes.io/instance=consumer -f
```

### 📊 Streamlit

Iniciar o **Streamlit**:

```bash
make start-streamlit
```

Parar o **Streamlit**:

```bash
make stop-streamlit
```

Logs do **Streamlit**:

```bash
kubectl logs -n steam -l app=streamlit -f
```

## 📈 **AutoScaling Automático e Limitações de Recursos**  

O **Horizontal Pod Autoscaler (HPA)** é configurado para escalar automaticamente os pods com base na **utilização de CPU e memória**. Além disso, cada serviço tem restrições de **recursos máximos e mínimos** para garantir eficiência no uso do Kubernetes.

### ⚙️ **Configuração de AutoScaling e Recursos por Serviço**  

### 🏗️ **Consumer** (**Escala automática ativada**)  
O **Consumer** escala automaticamente entre **1 e 6 réplicas** com base no uso de CPU e memória. Aumenta quando a utilização ultrapassa **70%** e reduz rapidamente quando cai abaixo de **50%**.

```yaml
resources:
  limits:
    cpu: 200m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 1
  maxReplicas: 6
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 30  # Tempo de espera reduzido para 30s antes de reduzir réplicas
      policies:
        - type: Percent
          value: 100  # Remove todas as réplicas de uma vez, se possível
          periodSeconds: 15  # Verifica a cada 15s se pode reduzir
      selectPolicy: Min
      scaleDownUtilizationThreshold: 0.5  # Se o uso cair abaixo de 50%, começa a reduzir
```

### 🏭 **Producer** (**1 réplica fixa**)  
O **Producer** não precisa de escalonamento automático, pois a lógica de processamento de mensagens depende apenas dos **Consumers**. Ele opera sempre com **1 pod fixo**.

```yaml
resources:
  limits:
    cpu: 300m
    memory: 100Mi
  requests:
    cpu: 150m
    memory: 64Mi
```

### 🐇 **RabbitMQ** (**1 réplica fixa**)  
O **RabbitMQ** opera com **1 única instância** e possui um limite de CPU e memória para evitar consumo excessivo.

```yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi
```

### 📊 **Streamlit** (**1 réplica fixa**)  
O **Streamlit** é a interface de monitoramento e visualização, então **não precisa de escalonamento**. Mantemos apenas **1 pod fixo** para evitar desperdício de recursos.

```yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi
```

---

## 🚀 **Resumo das Configurações**  

| Serviço    | Escala | Mínimo de Réplicas | Máximo de Réplicas | CPU Máxima | Memória Máxima |
|------------|--------|--------------------|--------------------|------------|----------------|
| **Consumer** | **Automático** | 1 | 6 | 200m | 512Mi |
| **Producer** | Fixo | 1 | 1 | 300m | 100Mi |
| **RabbitMQ** | Fixo | 1 | 1 | 500m | 512Mi |
| **Streamlit** | Fixo | 1 | 1 | 500m | 512Mi |

---

### 🔄 **Como Funciona o AutoScaling?**  

1. **Consumer Escala Automático:** Se a CPU/memória ultrapassar **70%**, novos pods serão adicionados até **6 réplicas**.
2. **Redução Rápida:** Se a utilização cair abaixo de **50%**, os pods começam a ser removidos em até **15 segundos**.
3. **Producer, RabbitMQ e Streamlit são fixos:** Mantêm **1 réplica única** para estabilidade e controle de recursos.

Essa configuração garante **eficiência no uso dos recursos**, escalando apenas o necessário e reduzindo rapidamente para evitar custos desnecessários! 🚀
