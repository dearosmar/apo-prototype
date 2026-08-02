import Foundation

enum APIError: LocalizedError {
    case server(String)
    case network

    var errorDescription: String? {
        switch self {
        case .server(let detail): return detail
        case .network: return "서버에 연결하지 못했어요. 맥의 백엔드가 켜져 있는지, 같은 Wi-Fi인지 확인해 주세요."
        }
    }
}

struct APIClient {
    static let shared = APIClient()

    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = Config.requestTimeout
        return URLSession(configuration: config)
    }()

    func checkDocument(text: String, filename: String = "scan.txt") async throws -> DocCheckResponse {
        let boundary = "Boundary-\(UUID().uuidString)"
        var request = URLRequest(url: Config.baseURL.appendingPathComponent("doc-check"))
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: text/plain\r\n\r\n".data(using: .utf8)!)
        body.append(text.data(using: .utf8)!)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        return try await send(request)
    }

    private func send(_ request: URLRequest) async throws -> DocCheckResponse {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.network
        }
        guard let http = response as? HTTPURLResponse else { throw APIError.network }
        guard http.statusCode == 200 else {
            if let detail = try? JSONDecoder().decode([String: String].self, from: data)["detail"] {
                throw APIError.server(detail)
            }
            throw APIError.server("요청 실패 (\(http.statusCode))")
        }
        return try JSONDecoder().decode(DocCheckResponse.self, from: data)
    }
}
