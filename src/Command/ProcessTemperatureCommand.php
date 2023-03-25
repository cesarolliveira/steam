<?php

namespace App\Command;

use App\Service\ProcessTemperatureService;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;

class ProcessTemperatureCommand extends Command
{
    protected static $defaultName = 'process:temperature';

    private $processTemperatureService;

    public function __construct(ProcessTemperatureService $processTemperatureService)
    {
        parent::__construct();
        $this->processTemperatureService = $processTemperatureService;
    }

    protected function configure()
    {
        $this
            ->setDescription('Process input file temperatures and generate output file.')
        ;
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $output->writeln([
            '=============================================',
            '|          Processing temperatures          |',
            '=============================================',
        ]);

        $result = $this->processTemperatureService->execute();

        $output->writeln([
            '| Read file time: '.$result['readFileTime'].'                      |',
            '| Process temperatures time: '.$result['processTemperaturesTime'].'           |',
            '| Total de sensores: '.$result['total_sensor'].'                      |',
            '| Total de temperatures read: '.count($result['temperatures']).'          |',
            '=============================================',
        ]);

        $output->writeln([
            '|                   Done!                   |',
            '=============================================',
        ]);

        return Command::SUCCESS;
    }
}
