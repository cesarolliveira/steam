<?php

namespace App\Service;

class ProcessTemperatureService
{
    private const INPUT_FILE = 'temperature.csv';
    private const OUTPUT_FILE_JSON = 'result.json';
    private const OUTPUT_FILE_TXT = 'result.txt';

    private $arraySum = [];

    public function execute(): array
    {
        $dataInputFile = $this->readInputFile();
        $processedTemperatures = $this->processTemperatures($dataInputFile);

        // Exporta os dados para o arquivo JSON
        $this->exportJson($processedTemperatures);

        // Exporta os dados para o arquivo TXT
        $this->exportTxt($processedTemperatures);

        return [
            'readFileTime' => $dataInputFile['readFileTime'],
            'processTemperaturesTime' => $processedTemperatures['processTemperaturesTime'],
        ];
    }

    private function readInputFile(): array
    {
        // Inicia o contador de tempo
        $startTime = microtime(true);

        // Lê o arquivo CSV
        $file = fopen(self::INPUT_FILE, "r");

        // Inicializa as variáveis para armazenar os dados e as estatísticas
        $data = [
            'temperatures' => [],
            'readFileTime' => null,
            'columns' => [],
        ];

        // Pega o nome das colunas do arquivo CSV
        $header = fgetcsv($file);
        $columns = explode(';', $header[0]);

        // Loop através das linhas do arquivo CSV
        while (($line = fgetcsv($file)) !== false) {
            // Separa os valores das colunas
            $values = explode(';', $line[0]);

            // Loop através dos valores das colunas
            foreach ($values as $key => $value) {
                // Armazena os valores das colunas
                $data['temperatures'][] = [
                    'column' => $columns[$key],
                    'value' => $value,
                ];
            }
        }

        // Fecha o arquivo CSV
        fclose($file);

        // Calcula o tempo de leitura do arquivo
        $endTime = microtime(true);

        $data['readFileTime'] = number_format($endTime - $startTime, 2);

        return $data;
    }

    private function calculateSum(float $data, int $maxSum = 5): float
    {
        $this->arraySum[] = $data;

        if (count($this->arraySum) > $maxSum) {
            array_shift($this->arraySum);
        }

        return array_sum($this->arraySum);
    }

    private function calculateStandardDeviation(array $data): float
    {
        $mean = array_sum($data) / count($data);

        $sum = 0;

        foreach ($data as $value) {
            $sum += pow($value - $mean, 2);
        }

        return sqrt($sum / count($data));
    }

    private function processTemperatures(array $data): array
    {
        // Inicia o contador de tempo
        $startTime = microtime(true);

        $result = [];

        for ($i=0; $i < count($data['temperatures']); $i++) {
            $date = new \DateTimeImmutable();
            $currentValue = $data['temperatures'][$i]['value'];
            $lastResult = end($result);

            if ($i === 0) {
                $result[] = [
                    'id' => $i + 1,
                    'sensor' => $data['temperatures'][$i]['column'],
                    'value' => $currentValue,
                    'unit' => 'C',
                    'timestamp' => $date->getTimestamp(),
                    'min' => $currentValue,
                    'max' => $currentValue,
                    'sum' => $this->calculateSum($currentValue),
                    'count' => 1,
                    'mean' => $currentValue,
                    'standardDeviation' => number_format($this->calculateStandardDeviation($this->arraySum), 2),
                ];

                continue;
            }

            $result[] = [
                'id' => $i + 1,
                'sensor' => $data['temperatures'][$i]['column'],
                'value' => $currentValue,
                'unit' => 'C',
                'timestamp' => $date->getTimestamp(),
                'min' => min($lastResult['min'], $currentValue),
                'max' => max($lastResult['max'], $currentValue),
                'sum' => $this->calculateSum($currentValue),
                'count' => $lastResult['count'] + 1 <= 5 ? $lastResult['count'] + 1 : 5,
                'mean' => ($lastResult['value'] + $currentValue) / 2,
                'standardDeviation' => number_format($this->calculateStandardDeviation($this->arraySum), 2),
            ];
        }

        // Calcula o tempo de leitura do arquivo
        $endTime = microtime(true);

        $result['processTemperaturesTime'] = number_format($endTime - $startTime, 2);

        return $result;
    }

    private function exportJson(array $data): void
    {
        // Remove os dados que não serão exportados
        unset($data['processTemperaturesTime']);

        $json = json_encode($data);

        if (!file_exists(self::OUTPUT_FILE_JSON)) {
            touch(self::OUTPUT_FILE_JSON);
        }

        file_put_contents(self::OUTPUT_FILE_JSON, $json);
    }

    private function exportTxt(array $data): void
    {
        if (!file_exists(self::OUTPUT_FILE_TXT)) {
            touch(self::OUTPUT_FILE_TXT);
        }

        // Recupera o nome das colunas
        $columns = array_keys($data[0]);

        // Adiciona as colunas no início do array
        array_unshift($data, $columns);

        // Abre o arquivo para escrita
        $export = fopen(self::OUTPUT_FILE_TXT, 'w');

        // Loop através dos dados
        foreach ($data as $row) {
            fputcsv(
                $export,
                $row,
                "\t",
            );
        }

        // Fecha o arquivo
        fclose($export);
    }
}
