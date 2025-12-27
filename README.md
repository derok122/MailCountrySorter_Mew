# MailCountrySorter (reimplementado em Python)

Uso rápido:

```bash
python mail_country_sorter.py --input emails.txt --output saída
```

Opções principais:
- `--input` (`-i`): arquivo com e-mails (uma linha por e-mail)
- `--tld-map` (`-m`): arquivo `Tld.map` (padrão: `Tld.map`)
- `--settings` (`-s`): `Setting.ini` (padrão: `Setting.ini`)
- `--output` (`-o`): diretório de saída (padrão: `output`)
- `--threads` (`-t`): override do número de threads

- `--format` (`-f`): `files` (um arquivo por país) ou `csv` (um CSV único)
- `--log`: caminho para arquivo de log (opcional)

Recomenda-se criar um ambiente virtual e instalar dependências:

```powershell
python -m venv venv
.\venv\Scripts\python -m pip install --upgrade pip
.\venv\Scripts\python -m pip install -r requirements.txt
```

Build (EXE) com ícone e assinatura:

```powershell
# exemplo: usar ícone app.ico e certificado cert.pfx
.\build_exe.ps1 -IconPath .\app.ico -PfxPath .\cert.pfx -PfxPassword MyPfxPassword
```

Notas:
- A assinatura requer `signtool.exe` (Windows SDK) disponível no `PATH`, ou forneça um certificado válido.
- O script incluirá `Tld.map`, `Setting.ini` e `Country.mmdb` no EXE.

O programa agrupa e-mails por país a partir do sufixo do domínio (TLD) e gera um arquivo por país.
