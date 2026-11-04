import AVFoundation
import CoreMedia
import Foundation

@main
struct MediaProbe {
    static func main() async {
        do {
            guard CommandLine.arguments.count == 2 else { throw ProbeError.usage }
            let url = URL(fileURLWithPath: CommandLine.arguments[1])
            let asset = AVURLAsset(url: url)
            let duration = try await asset.load(.duration).seconds
            let tracks = try await asset.load(.tracks)
            var streams: [[String: Any]] = []
            for track in tracks {
                let type = track.mediaType
                let descriptions = try await track.load(.formatDescriptions)
                let subtype = descriptions.first.map { CMFormatDescriptionGetMediaSubType($0) }
                let codec = subtype.map(fourCC) ?? "unknown"
                if type == .video {
                    let size = try await track.load(.naturalSize)
                    let rate = try await track.load(.nominalFrameRate)
                    let frameRate: String
                    if rate >= 0 && abs(rate - rate.rounded()) < 0.001 {
                        frameRate = "\(Int(rate.rounded()))/1"
                    } else {
                        frameRate = "\(Int((rate * 1000).rounded()))/1000"
                    }
                    streams.append(["codec_type": "video", "codec_name": codec,
                                    "width": Int(abs(size.width).rounded()),
                                    "height": Int(abs(size.height).rounded()),
                                    "avg_frame_rate": frameRate])
                } else if type == .audio {
                    streams.append(["codec_type": "audio", "codec_name": codec])
                }
            }
            let output: [String: Any] = ["format": ["duration": String(duration)], "streams": streams]
            let data = try JSONSerialization.data(withJSONObject: output, options: [.sortedKeys])
            print(String(decoding: data, as: UTF8.self))
        } catch {
            fputs("media probe failed: \(error)\n", stderr)
            exit(2)
        }
    }

    static func fourCC(_ code: FourCharCode) -> String {
        let bytes: [UInt8] = [UInt8((code >> 24) & 0xff), UInt8((code >> 16) & 0xff), UInt8((code >> 8) & 0xff), UInt8(code & 0xff)]
        return String(bytes: bytes, encoding: .macOSRoman)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? "unknown"
    }
}

enum ProbeError: Error { case usage }
