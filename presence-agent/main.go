package main

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"sync"
	"time"
)

type Config struct { ServerURL string `json:"server_url"`; Token string `json:"token"` }
type State struct { Installed bool `json:"installed"`; Enrolled bool `json:"enrolled"`; Platform string `json:"platform"`; Version string `json:"version"`; WorkState string `json:"work_state"` }

var version = "test-0.3.3"
var allowedOrigin = "http://185.164.172.211:8080"
var mu sync.RWMutex
var config Config
var lastReminder string
var currentWorkState = "not_started"

func configPath() string {
	base, _ := os.UserConfigDir()
	return filepath.Join(base, "SupportBotPresence", "config.json")
}
func loadConfig() { data, err := os.ReadFile(configPath()); if err == nil { _ = json.Unmarshal(data, &config) } }
func saveConfig() error {
	if err := os.MkdirAll(filepath.Dir(configPath()), 0700); err != nil { return err }
	data, _ := json.Marshal(config)
	return os.WriteFile(configPath(), data, 0600)
}
func originAllowed(origin string) bool {
	if origin == allowedOrigin { return true }
	mu.RLock(); server := config.ServerURL; mu.RUnlock()
	parsed, err := url.Parse(server)
	return err == nil && server != "" && origin == parsed.Scheme+"://"+parsed.Host
}
func cors(w http.ResponseWriter, r *http.Request) bool {
	origin := r.Header.Get("Origin")
	if !originAllowed(origin) { w.WriteHeader(http.StatusForbidden); return false }
	w.Header().Set("Access-Control-Allow-Origin", origin)
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	return true
}
func localServer() {
	http.HandleFunc("/status", func(w http.ResponseWriter, r *http.Request) {
		if !cors(w, r) { return }; if r.Method == "OPTIONS" { return }
		mu.RLock(); enrolled := config.Token != "" && config.ServerURL != ""; workState := currentWorkState; mu.RUnlock()
		_ = json.NewEncoder(w).Encode(State{true, enrolled, runtime.GOOS, version, workState})
	})
	http.HandleFunc("/enroll", func(w http.ResponseWriter, r *http.Request) {
		if !cors(w, r) { return }; if r.Method == "OPTIONS" { return }; if r.Method != "POST" { w.WriteHeader(405); return }
		var next Config; if json.NewDecoder(r.Body).Decode(&next) != nil || next.Token == "" || next.ServerURL == "" { w.WriteHeader(400); return }
		mu.Lock(); config = next; err := saveConfig(); mu.Unlock()
		if err != nil { w.WriteHeader(500); return }; w.WriteHeader(204)
	})
	http.HandleFunc("/control", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" { w.WriteHeader(405); return }
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write([]byte(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>SupportBot Presence</title><style>body{font:15px system-ui;background:#17191d;color:#f4f1eb;margin:0;padding:24px}main{max-width:420px;margin:auto}button{display:block;width:100%;margin:9px 0;padding:14px;border:0;border-radius:14px;font-weight:700;cursor:pointer}h1{font-size:24px}h2{margin-top:24px;font-size:15px;color:#d4b36e}#status{color:#d4b36e;min-height:22px}</style><main><h1>Рабочий статус</h1><p id="status"></p><button data-s="working">Начать рабочий день / вернуться к работе</button><button data-s="lunch">Обед</button><button data-s="break">Перерыв</button><button data-s="meeting">Совещание</button><button data-s="other">Прочая причина</button><h2>Официальное отсутствие</h2><button data-s="vacation">Отпуск</button><button data-s="sick_leave">Больничный</button><button data-s="business_trip">Командировка</button><button data-s="day_off">Отгул</button><button data-s="finished">Завершить рабочий день</button></main><script>document.querySelectorAll('button').forEach(b=>b.onclick=()=>{let official=['vacation','sick_leave','business_trip','day_off'].includes(b.dataset.s),reason=b.dataset.s==='other'?prompt('Укажите причину отсутствия'):'',start=official?prompt('Начало (YYYY-MM-DDTHH:MM)'):'',end=official?prompt('Окончание (YYYY-MM-DDTHH:MM)'):'';if((b.dataset.s==='other'&&!reason)||(official&&(!start||!end)))return;fetch('/work-state',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({state:b.dataset.s,reason:reason||'',starts_at:start||'',ends_at:end||''})}).then(r=>r.json()).then(x=>document.querySelector('#status').textContent=x.label||x.error)});</script>`))
	})
	http.HandleFunc("/work-state", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "GET" { mu.RLock(); state := currentWorkState; mu.RUnlock(); _ = json.NewEncoder(w).Encode(map[string]string{"state": state}); return }
		if r.Method != "POST" { w.WriteHeader(405); return }
		var payload map[string]string; if json.NewDecoder(r.Body).Decode(&payload) != nil { w.WriteHeader(400); return }
		result, status := sendWorkState(payload["state"], payload["reason"], payload["starts_at"], payload["ends_at"]); w.WriteHeader(status); _, _ = w.Write(result)
	})
	log.Println(http.ListenAndServe("127.0.0.1:47831", nil))
}
func sendWorkState(state, reason, startsAt, endsAt string) ([]byte, int) {
	mu.RLock(); c := config; mu.RUnlock()
	if c.Token == "" || c.ServerURL == "" { return []byte(`{"error":"Агент не подключён"}`), 409 }
	body, _ := json.Marshal(map[string]string{"state": state, "reason": reason, "starts_at": startsAt, "ends_at": endsAt})
	req, _ := http.NewRequest("POST", c.ServerURL+"/api/agent/work-state", bytes.NewReader(body))
	req.Header.Set("Authorization", "Bearer "+c.Token); req.Header.Set("Content-Type", "application/json")
	client := &http.Client{Timeout: 8*time.Second}; resp, err := client.Do(req)
	if err != nil { return []byte(`{"error":"Сервис недоступен"}`), 503 }; defer resp.Body.Close()
	var response bytes.Buffer; _, _ = response.ReadFrom(resp.Body)
	if resp.StatusCode >= 200 && resp.StatusCode < 300 { var value struct { State string `json:"state"` }; if json.Unmarshal(response.Bytes(), &value) == nil && value.State != "" { mu.Lock(); currentWorkState = value.State; mu.Unlock() } }
	return response.Bytes(), resp.StatusCode
}
func heartbeat() {
	for {
		mu.RLock(); c := config; mu.RUnlock()
		if c.Token != "" && c.ServerURL != "" {
			idle, locked := systemPresence()
			body, _ := json.Marshal(map[string]any{"idle_seconds": int(idle.Seconds()), "locked": locked, "platform": runtime.GOOS, "version": version})
			req, _ := http.NewRequest("POST", c.ServerURL+"/api/agent/heartbeat", bytes.NewReader(body))
			req.Header.Set("Authorization", "Bearer "+c.Token); req.Header.Set("Content-Type", "application/json")
			client := &http.Client{Timeout: 8 * time.Second}; if resp, err := client.Do(req); err == nil {
				var result struct { Reminder string `json:"reminder"`; State string `json:"state"` }
				_ = json.NewDecoder(resp.Body).Decode(&result); resp.Body.Close()
				if result.State != "" { mu.Lock(); currentWorkState = result.State; mu.Unlock() }
				if result.Reminder != "" && result.Reminder != lastReminder { showNotification("SupportBot Presence", result.Reminder) }
				lastReminder = result.Reminder
			}
		}
		time.Sleep(20 * time.Second)
	}
}
func main() { loadConfig(); go localServer(); heartbeat() }
