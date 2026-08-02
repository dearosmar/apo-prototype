import AVFoundation
import SwiftUI

struct ScanFlowView: View {
    enum Phase {
        case scanning
        case recognizing
        case review
    }

    @Environment(\.dismiss) private var dismiss
    @State private var phase: Phase = .scanning
    @State private var recognizedText = ""
    @State private var errorMessage: String?
    @State private var loading = false
    @State private var report: DocCheckResponse?
    @State private var navigate = false

    var body: some View {
        Group {
            switch phase {
            case .scanning:
                scannerOrFallback
            case .recognizing:
                VStack(spacing: 16) {
                    ProgressView()
                    Text("글자를 읽고 있어요… (중국어·한국어)")
                        .foregroundStyle(.secondary)
                }
            case .review:
                reviewView
            }
        }
        .navigationTitle("서류 스캔")
        .navigationBarTitleDisplayMode(.inline)
        .navigationDestination(isPresented: $navigate) {
            if let report {
                ReportView(report: report)
            }
        }
    }

    @ViewBuilder
    private var scannerOrFallback: some View {
        if ScannerView.isSupported && AVCaptureDevice.authorizationStatus(for: .video) != .denied {
            ScannerView(
                onFinish: { images in
                    phase = .recognizing
                    Task { await recognize(images) }
                },
                onCancel: { dismiss() },
                onError: { error in
                    errorMessage = error.localizedDescription
                    phase = .review
                }
            )
            .ignoresSafeArea()
        } else {
            VStack(spacing: 14) {
                Text("📷")
                    .font(.system(size: 48))
                Text(ScannerView.isSupported
                    ? "카메라 권한이 꺼져 있어요.\n설정 > 바다 건너 사장님에서 카메라를 허용해 주세요."
                    : "이 기기에서는 문서 스캔을 지원하지 않아요.\n(시뮬레이터에서는 아래 샘플로 확인해 보세요)")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                Button("중국어 샘플 PI로 계속하기") {
                    recognizedText = SampleData.riskyPI
                    phase = .review
                }
                .buttonStyle(.borderedProminent)
                .tint(AppColor.navy)
            }
            .padding()
        }
    }

    private var reviewView: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("인식된 내용을 확인·수정하세요")
                .font(.headline)
                .foregroundStyle(AppColor.navy)
            Text("오인식된 글자가 있으면 여기서 바로 고칠 수 있어요.")
                .font(.caption)
                .foregroundStyle(.secondary)
            TextEditor(text: $recognizedText)
                .font(.system(size: 14, design: .monospaced))
                .padding(8)
                .background(RoundedRectangle(cornerRadius: 10).stroke(Color(.systemGray4)))
            if let errorMessage {
                Text(errorMessage)
                    .font(.footnote)
                    .foregroundStyle(AppColor.red)
            }
            Button {
                Task { await submit() }
            } label: {
                if loading {
                    ProgressView().frame(maxWidth: .infinity)
                } else {
                    Text("이 내용으로 점검 요청")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                }
            }
            .padding()
            .background(AppColor.yellow)
            .foregroundStyle(AppColor.navy)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .disabled(loading || recognizedText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
        .padding()
    }

    private func recognize(_ images: [UIImage]) async {
        do {
            recognizedText = try await OCRService.recognize(images: images)
            errorMessage = nil
        } catch {
            recognizedText = ""
            errorMessage = error.localizedDescription
        }
        phase = .review
    }

    private func submit() async {
        loading = true
        errorMessage = nil
        do {
            report = try await APIClient.shared.checkDocument(text: recognizedText)
            navigate = true
        } catch {
            errorMessage = error.localizedDescription
        }
        loading = false
    }
}
