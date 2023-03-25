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
        $data = $this->readInputFile();
        $data['temperatures'] = $this->processTemperatures($data);
        $data['processTemperaturesTime'] = $data['temperatures']['processTemperaturesTime'];
        unset($data['temperatures']['processTemperaturesTime']);
        $result = $this->calculateOutliers($data['temperatures']);

        // Exporta os dados para o arquivo JSON
        $this->exportJson($result['data']);

        // Exporta os dados para o arquivo TXT
        $this->exportTxt($result['data']);

        return $data;
    }

    private function readInputFile(): array
    {
        // Inicia o contador de tempo
        $startTime = microtime(true);

        // Lê o arquivo CSV
        $file = fopen(self::INPUT_FILE, 'r');

        // Inicializa as variáveis para armazenar os dados e as estatísticas
        $data = [
            'temperatures' => [],
            'readFileTime' => null,
        ];

        // Pega o nome das colunas do arquivo CSV
        $header = fgetcsv($file);
        $sensor = explode(';', $header[0]);

        // Loop através das linhas do arquivo CSV
        while (($line = fgetcsv($file)) !== false) {
            // Separa os valores das colunas
            $values = explode(';', $line[0]);

            // Loop através dos valores das colunas
            foreach ($values as $key => $value) {
                // Armazena os valores das colunas
                $data['temperatures'][] = [
                    'sensor' => $sensor[$key],
                    'value' => $value,
                ];
            }
        }

        // Fecha o arquivo CSV
        fclose($file);

        // Calcula o tempo de leitura do arquivo
        $endTime = microtime(true);

        $data['readFileTime'] = number_format($endTime - $startTime, 2);
        $data['total_sensor'] = count($sensor);

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

        for ($i = 0; $i < count($data['temperatures']); ++$i) {
            $date = new \DateTimeImmutable();
            $currentValue = $data['temperatures'][$i]['value'];
            $lastResult = end($result);

            if (0 === $i) {
                $result[] = [
                    'id' => $i + 1,
                    'sensor' => $data['temperatures'][$i]['sensor'],
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
                'sensor' => $data['temperatures'][$i]['sensor'],
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

    private function calculateQuartis(array $data): array
    {
        $temperatures = [];

        foreach ($data as $value) {
            $temperatures[] = $value['value'];
        }

        sort($temperatures);
        $count = count($data);
        $totalRows = count($temperatures);

        if (0 === $count % 2) {
            $Q1_1 = $temperatures[floor($totalRows + 1) / 4];
            $Q1_2 = $temperatures[floor($totalRows / 4 + 1)];
            $Q1 = number_format($Q1_1 + (0.25 * ($Q1_2 - $Q1_1)), 2, '.', '');
        } else {
            $Q1 = $totalRows / 4;
        }

        $Q2 = array_sum($temperatures) / count($temperatures);

        if (0 === $count % 2) {
            $Q3_1 = $temperatures[3 * floor($totalRows / 4)];
            $Q3_2 = $temperatures[3 * floor($totalRows / 4) + 1];
            $Q3 = number_format($Q3_1 + (0.75 * ($Q3_2 - $Q3_1)), 2, '.', '');
        } else {
            $Q3 = ($totalRows / 4) * 3;
        }

        return [
            'Q1' => $Q1,
            'Q2' => $Q2,
            'Q3' => $Q3,
        ];
    }

    private function calculateIQR($data): array
    {
        $quartis = $this->calculateQuartis($data);

        $iqr = $quartis['Q3'] - $quartis['Q1'];

        $median_min = $quartis['Q2'] - (1.5 * $iqr);
        $median_max = $quartis['Q2'] + (1.5 * $iqr);

        return [
            'iqr' => $iqr,
            'median_min' => $median_min,
            'median_max' => $median_max,
        ];
    }

    private function calculateOutliers(array $data): array
    {
        $result = $this->calculateIQR($data);

        $outliers = [];

        foreach ($data as $key => $temperature) {
            if ($temperature['value'] < $result['median_min'] || $temperature['value'] > $result['median_max']) {
                $outliers[] = array_merge_recursive($temperature, ['outliers' => 'outliers']);
                $data[$key]['outliers'] = 'outliers';
            } else {
                $data[$key]['outliers'] = 'normal';
            }
        }

        return [
            'outliers' => $outliers,
            'data' => $data,
        ];
    }
}
