import Foundation

enum Config {
    // 실기기는 localhost로 맥에 못 붙는다 — 맥의 LAN IP 사용 (ipconfig getifaddr en0)
    static let baseURL = URL(string: "http://172.30.1.98:8000")!
    static let requestTimeout: TimeInterval = 90
}
