import AppKit
import Foundation

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var item: NSStatusItem!
    private let states = [
        ("Начать рабочий день", "working"),
        ("Уйти на обед", "lunch"),
        ("Уйти на перерыв", "break"),
        ("Уйти на совещание", "meeting"),
        ("Отойти по прочей причине", "other"),
        ("Завершить рабочий день", "finished"),
    ]

    func applicationDidFinishLaunching(_ notification: Notification) {
        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        item.button?.image = NSImage(systemSymbolName: "person.crop.circle.badge.clock", accessibilityDescription: "SupportBot Presence")
        let menu = NSMenu()
        menu.addItem(withTitle: "SupportBot Presence", action: #selector(openControl), keyEquivalent: "")
        menu.addItem(.separator())
        for (title, state) in states {
            let entry = NSMenuItem(title: title, action: #selector(changeState(_:)), keyEquivalent: "")
            entry.representedObject = state
            entry.target = self
            menu.addItem(entry)
        }
        item.menu = menu
    }

    @objc private func openControl() {
        NSWorkspace.shared.open(URL(string: "http://127.0.0.1:47831/control")!)
    }

    @objc private func changeState(_ sender: NSMenuItem) {
        guard let state = sender.representedObject as? String,
              let url = URL(string: "http://127.0.0.1:47831/work-state") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["state": state])
        URLSession.shared.dataTask(with: request).resume()
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
