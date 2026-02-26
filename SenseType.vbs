' ============================================
'  SenseType - 本地语音输入（无控制台窗口版）
'  双击启动，自动请求管理员权限
' ============================================

Set Shell = CreateObject("Shell.Application")
' 以管理员身份运行 bat 脚本，0 = 隐藏窗口
Shell.ShellExecute "cmd.exe", "/c """ & Replace(WScript.ScriptFullName, ".vbs", ".bat") & """", "", "runas", 0
