# Registra (ou atualiza) as tarefas do Boletim no Agendador do Windows. Sem administrador:
#   powershell -ExecutionPolicy Bypass -File agendar.ps1
#   powershell -ExecutionPolicy Bypass -File agendar.ps1 -SemSessao      # roda sem sessao aberta (pede a senha do Windows)
#   powershell -ExecutionPolicy Bypass -File agendar.ps1 -Hora "05:30" -HoraVigia "07:30"
#
# "Boletim diario"         coleta, IA, painel, e-mail e Telegram (todas as edicoes)
# "Boletim diario - vigia" se o painel de hoje nao existir ate HoraVigia, avisa no Telegram/e-mail
# Horario padrao 05:30; a vigia avisa se o painel nao saiu.

param(
    [string]$Hora = "05:30",
    [string]$HoraVigia = "07:30",
    [switch]$SemSessao
)

$config = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 15)

if ($SemSessao) {
    $cred = Get-Credential -UserName "$env:USERDOMAIN\$env:USERNAME" -Message "Senha do Windows para a tarefa rodar sem sessao aberta"
    $registro = @{ User = $cred.UserName; Password = $cred.GetNetworkCredential().Password }
} else {
    $registro = @{ Principal = (New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited) }
}

function Registrar($nome, $argumentos, $quando, $descricao) {
    $acao = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$(Join-Path $PSScriptRoot 'rodar.cmd')`" $argumentos"
    Register-ScheduledTask -TaskName $nome -Action $acao -Trigger (New-ScheduledTaskTrigger -Daily -At $quando) `
        -Settings $config -Description $descricao -Force @registro | Out-Null
}

Registrar "Boletim diario" "" $Hora "Newsletter diaria: painel HTML offline, e-mail e Telegram"
Registrar "Boletim diario - vigia" "--vigiar" $HoraVigia "Avisa se o Boletim diario nao saiu hoje"

Get-ScheduledTask -TaskName "Boletim diario*" | ForEach-Object {
    $i = $_ | Get-ScheduledTaskInfo
    [pscustomobject]@{ Tarefa = $_.TaskName; Proxima = $i.NextRunTime; Logon = $_.Principal.LogonType }
}
