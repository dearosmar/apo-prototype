import UIKit
import Vision

enum OCRError: LocalizedError {
    case empty

    var errorDescription: String? {
        "글자를 인식하지 못했어요. 문서가 잘 보이게 다시 촬영해 주세요."
    }
}

enum OCRService {
    static func recognize(images: [UIImage]) async throws -> String {
        var pages: [String] = []
        for image in images {
            guard let cgImage = image.cgImage else { continue }
            let text = try await recognize(cgImage: cgImage)
            if !text.isEmpty { pages.append(text) }
        }
        let joined = pages.joined(separator: "\n")
        guard !joined.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw OCRError.empty
        }
        return joined
    }

    private static func recognize(cgImage: CGImage) async throws -> String {
        try await withCheckedThrowingContinuation { continuation in
            let request = VNRecognizeTextRequest { request, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                let observations = request.results as? [VNRecognizedTextObservation] ?? []
                let lines = observations.compactMap { $0.topCandidates(1).first?.string }
                continuation.resume(returning: lines.joined(separator: "\n"))
            }
            request.recognitionLanguages = ["zh-Hans", "ko-KR"]
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = true

            DispatchQueue.global(qos: .userInitiated).async {
                do {
                    try VNImageRequestHandler(cgImage: cgImage).perform([request])
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }
}
