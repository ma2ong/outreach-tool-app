' Start the Cloudflare tunnel with no console window.
' cloudflared is a console program, so a scheduled task would flash a black box
' on every logon; WScript.Shell.Run with mode 0 keeps it invisible.
Dim fso, root, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
cmd = """" & root & "\bin\cloudflared.exe"" tunnel run maxcolor-crm"
CreateObject("WScript.Shell").Run cmd, 0, False
