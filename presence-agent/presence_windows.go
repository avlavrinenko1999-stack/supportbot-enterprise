//go:build windows

package main

import (
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

func init() {
	current, err := os.Executable(); if err != nil { return }
	targetDir := filepath.Join(os.Getenv("LOCALAPPDATA"), "SupportBotPresence")
	target := filepath.Join(targetDir, "supportbot-presence.exe")
	if strings.EqualFold(filepath.Clean(current), filepath.Clean(target)) { startWindowsTray(targetDir); return }
	_ = os.MkdirAll(targetDir, 0700)
	_ = os.Remove(target + ".old")
	_ = os.Rename(target, target+".old")
	source, err := os.Open(current); if err != nil { return }; defer source.Close()
	destination, err := os.Create(target); if err != nil { return }
	_, copyErr := io.Copy(destination, source); closeErr := destination.Close()
	if copyErr != nil || closeErr != nil { return }
	command := `"` + target + `"`
	_ = exec.Command("schtasks.exe", "/Create", "/F", "/SC", "ONLOGON", "/RL", "LIMITED", "/TN", "SupportBot Presence", "/TR", command).Run()
	_ = exec.Command(target).Start()
	os.Exit(0)
}

func startWindowsTray(targetDir string) {
	script := filepath.Join(targetDir, "supportbot-tray.ps1")
	content := `$mutex = New-Object Threading.Mutex($true, "Global\SupportBotPresenceTray-" + $env:USERNAME, [ref]$created)
if (-not $created) { exit }
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName Microsoft.VisualBasic
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Application
$n.Text = "SupportBot Presence"
$n.Visible = $true
$m = New-Object System.Windows.Forms.ContextMenuStrip
function Set-WorkState($state, $reason = "", $startsAt = "", $endsAt = "") { @{state=$state;reason=$reason;starts_at=$startsAt;ends_at=$endsAt} | ConvertTo-Json | %{ Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:47831/work-state" -ContentType "application/json" -Body $_ } | Out-Null }
$working = $m.Items.Add("Начать рабочий день")
$working.Add_Click({ Set-WorkState "working" })
$leave = $m.Items.Add("Покинуть рабочее место")
foreach ($pair in @(@("Обед","lunch"),@("Перерыв","break"),@("Совещание","meeting"))) { $i=$leave.DropDownItems.Add($pair[0]); $state=$pair[1]; $i.Add_Click({ Set-WorkState $state }.GetNewClosure()) }
$other = $leave.DropDownItems.Add("Прочая причина")
$other.Add_Click({ $reason=[Microsoft.VisualBasic.Interaction]::InputBox("Опишите причину отсутствия на рабочем месте.","Прочая причина",""); if ($reason.Trim()) { if ([System.Windows.Forms.MessageBox]::Show($reason,"Подтвердить причину?",[System.Windows.Forms.MessageBoxButtons]::OKCancel) -eq "OK") { Set-WorkState "other" $reason.Trim() } } })
$official = $m.Items.Add("Официальное отсутствие")
foreach ($pair in @(@("Отпуск","vacation"),@("Больничный","sick_leave"),@("Командировка","business_trip"),@("Отгул","day_off"))) { $i=$official.DropDownItems.Add($pair[0]); $state=$pair[1]; $i.Add_Click({ $start=[Microsoft.VisualBasic.Interaction]::InputBox("Начало (ГГГГ-ММ-ДДTЧЧ:ММ)","Период официального отсутствия",(Get-Date).AddMinutes(1).ToString("yyyy-MM-ddTHH:mm")); if(-not $start){return}; $end=[Microsoft.VisualBasic.Interaction]::InputBox("Окончание (ГГГГ-ММ-ДДTЧЧ:ММ)","Период официального отсутствия",(Get-Date).AddHours(8).ToString("yyyy-MM-ddTHH:mm")); if($end){Set-WorkState $state "" $start $end} }.GetNewClosure()) }
$finished = $m.Items.Add("Завершить рабочий день")
$finished.Add_Click({ Set-WorkState "finished" })
$m.Add_Opening({ try { $state=(Invoke-RestMethod -Uri "http://127.0.0.1:47831/work-state").state } catch { $state="not_started" }; $working.Visible=$state -ne "working" -and $state -notin @("vacation","sick_leave","business_trip","day_off"); $working.Text=if($state -eq "not_started" -or $state -eq "finished"){"Начать рабочий день"}else{"Вернуться к работе"}; $leave.Visible=$state -eq "working" })
$n.ContextMenuStrip = $m
$n.Add_MouseClick({ if ($_.Button -eq [System.Windows.Forms.MouseButtons]::Left) { Start-Process "http://127.0.0.1:47831/control" } })
[System.Windows.Forms.Application]::Run()
$n.Dispose()`
	_ = os.WriteFile(script, []byte(content), 0600)
	_ = exec.Command("powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", script).Start()
}

func showNotification(title, message string) {
	script := `Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; $n=New-Object System.Windows.Forms.NotifyIcon; $n.Icon=[System.Drawing.SystemIcons]::Information; $n.Visible=$true; $n.BalloonTipTitle=$args[0]; $n.BalloonTipText=$args[1]; $n.ShowBalloonTip(8000); Start-Sleep -Seconds 9; $n.Dispose()`
	_ = exec.Command("powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script, title, message).Start()
}

type lastInputInfo struct { Size uint32; Time uint32 }
var user32 = syscall.NewLazyDLL("user32.dll")
var getLastInputInfo = user32.NewProc("GetLastInputInfo")
var getTickCount = syscall.NewLazyDLL("kernel32.dll").NewProc("GetTickCount")
var openInputDesktop = user32.NewProc("OpenInputDesktop")
var closeDesktop = user32.NewProc("CloseDesktop")

func systemPresence() (time.Duration, bool) {
	info := lastInputInfo{Size: uint32(unsafe.Sizeof(lastInputInfo{}))}
	getLastInputInfo.Call(uintptr(unsafe.Pointer(&info)))
	nowTick, _, _ := getTickCount.Call()
	idle := time.Duration(uint32(nowTick)-info.Time) * time.Millisecond
	desktop, _, _ := openInputDesktop.Call(0, 0, 0x0100)
	locked := desktop == 0
	if desktop != 0 { closeDesktop.Call(desktop) }
	return idle, locked
}
