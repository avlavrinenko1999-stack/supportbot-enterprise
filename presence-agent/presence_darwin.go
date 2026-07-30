//go:build darwin

package main

import (
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"time"
)

func showNotification(title, message string) {
	script := `display notification ` + strconv.Quote(message) + ` with title ` + strconv.Quote(title)
	_ = exec.Command("/usr/bin/osascript", "-e", script).Start()
}

var idlePattern = regexp.MustCompile(`HIDIdleTime"\s*=\s*(\d+)`)

func systemPresence() (time.Duration, bool) {
	data, _ := exec.Command("/usr/sbin/ioreg", "-c", "IOHIDSystem").Output()
	match := idlePattern.FindStringSubmatch(string(data)); var idle time.Duration
	if len(match) == 2 { if ns, err := strconv.ParseInt(match[1], 10, 64); err == nil { idle = time.Duration(ns) } }
	root, _ := exec.Command("/usr/sbin/ioreg", "-n", "Root", "-d1").Output()
	locked := strings.Contains(string(root), "CGSSessionScreenIsLocked") && strings.Contains(string(root), "Yes")
	return idle, locked
}
