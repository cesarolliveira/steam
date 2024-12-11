
# Projeto Steam

## **Objetivo do Projeto**
 - Projeto de Monitoramento de Sensores da Caldeira Industrial.
 - Este projeto é destinado à leitura e processamento de dados provenientes de sensores instalados em uma caldeira industrial.
 - Os serviços principais, Producer e Consumer, desempenham os seguintes papéis:
  - Producer: Captura os dados em tempo real dos sensores da caldeira e os insere no sistema de mensageria RabbitMQ.
  - Consumer: Processa e analisa as mensagens recebidas, gerando insights ou acionando alertas em caso de anomalias ou falhas detectadas.
 - Este projeto utiliza Kubernetes para orquestrar serviço principal: `Consumer`. 
 - O `Producer` insere mensagens no RabbitMQ, enquanto o `Consumer` processa essas mensagens. 
 - O sistema usa o Helm para gerenciamento de deploys, e as imagens Docker dos serviços estão publicadas no Docker Hub.


---

## **1. Pré-requisitos**
- Kubernetes configurado e funcional.
- `kubectl` instalado e configurado.
- Helm instalado.
- RabbitMQ instalado via Helm Chart.
- Acesso ao Docker Hub.

---

## **2. Configuração Inicial**

### **2.1 Configurando o RabbitMQ**
1. **Adicionar o repositório do Helm:**
   ```bash
   helm repo add bitnami https://charts.bitnami.com/bitnami
   ```

2. **Instalar o RabbitMQ:**
   ```bash
   helm upgrade --install --create-namespace --namespace steam rabbitmq bitnami/rabbitmq --version 15.0.6 -f resources/rabbitmq/values.yaml
   ```

3. **Acessar o RabbitMQ:**
   - Endereço: `http://127.0.0.1:15672/`
   - Para obter a senha:
     ```bash
     kubectl get secret rabbitmq -n steam -o jsonpath="{.data.rabbitmq-password}" | base64 --decode
     ```

4. **Alterar a senha do usuário:**
   ```bash
   kubectl exec -it rabbitmq-0 -n steam -- rabbitmqctl authenticate_user user <nova_senha>
   ```

---

## **3. Construção e Publicação de Imagens Docker**

### **3.1 Producer**
1. **Construir a imagem:**
   ```bash
   docker build --file resources/producer/Dockerfile --no-cache --tag luisfeliphe66/producer:latest .
   ```

2. **Publicar no Docker Hub:**
   ```bash
   docker push luisfeliphe66/producer:latest
   ```

### **3.2 Consumer**
1. **Construir a imagem:**
   ```bash
   docker build --file resources/consumer/Dockerfile --no-cache --tag luisfeliphe66/consumer:test .
   ```

2. **Publicar no Docker Hub:**
   ```bash
   docker push luisfeliphe66/consumer:test
   ```

---

## **4. Deploy das Aplicações com Helm**

### **4.2 Consumer**
1. **Deploy:**
   ```bash
   helm upgrade --install --create-namespace --namespace steam consumer ./helm -f helm/values.yaml
   ```

2. **Acessar o pod:**
   ```bash
   kubectl exec -it consumer-8578569c98-2mb44 -n steam -- bash
   ```

---

## **5. Verificação e Debug**

### **5.1 Verificar os Recursos no Kubernetes**
```bash
kubectl get all -n steam
```

### **5.2 Debug Containers**
- Executar o `Producer` para debug:
  ```bash
  kubectl run producer -n steam --image luisfeliphe66/producer:latest
  ```
---

## **6. Desinstalação**

### **6.1 RabbitMQ**
```bash
helm uninstall -n steam rabbitmq
```

### **6.2 Consumer**
```bash
helm uninstall -n steam consumer
```

## **7. Upgrade**

### **7.1 Upgrade consumer**
```bash
helm upgrade --install --create-namespace --namespace steam consumer ./helm -f helm/values.yaml
```
## **8. auto-scaling**

```bash
watch kubectl get hpa -A
```
```bash
watch kubectl get pods -n steam
```
### **9. create/delete cronjob**
```bash
make delete-jobs
```
```bash
make delete-jobs
```
---

## **10. Estrutura de Arquivos do Projeto**
- **`helm`**: Configurações de deployment do Helm.
- **`Dockerfile`**: Dockerfile para o Producer e Consumer.
- **`resources/rabbitmq/values.yaml`**: Configurações específicas para o RabbitMQ.
