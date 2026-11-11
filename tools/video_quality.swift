import AVFoundation
import CoreGraphics
import Foundation

@main
struct VideoQuality {
    static func main() async {
        do {
            guard CommandLine.arguments.count == 2 else { throw QualityError.usage }
            let url = URL(fileURLWithPath: CommandLine.arguments[1])
            let asset = AVURLAsset(url: url)
            let duration = try await asset.load(.duration).seconds
            let allTracks = try await asset.load(.tracks)
            let tracks = allTracks.filter { track in track.mediaType == .video }
            guard tracks.count == 1, duration.isFinite, duration > 0 else { throw QualityError.invalidVideo }

            let generator = AVAssetImageGenerator(asset: asset)
            generator.appliesPreferredTrackTransform = true
            generator.maximumSize = CGSize(width: 160, height: 90)
            let samples = 12
            var reference: [UInt8]?
            var distinctFrames = 0
            var blackFrames = 0
            for index in 0..<samples {
                let seconds = duration * (Double(index) + 0.5) / Double(samples)
                let time = CMTime(seconds: seconds, preferredTimescale: 600)
                let (image, _) = try await generator.image(at: time)
                let width = image.width
                let height = image.height
                guard width > 0, height > 0 else { throw QualityError.invalidFrame }
                let bytesPerRow = width * 4
                guard let context = CGContext(data: nil, width: width, height: height,
                                              bitsPerComponent: 8, bytesPerRow: bytesPerRow,
                                              space: CGColorSpaceCreateDeviceRGB(),
                                              bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue |
                                                  CGBitmapInfo.byteOrder32Big.rawValue),
                      let data = context.data else { throw QualityError.invalidFrame }
                context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
                let bytes = data.assumingMemoryBound(to: UInt8.self)
                let pixels = width * height
                var litPixels = 0
                var differenceTotal = 0
                var changedPixels = 0
                for pixel in 0..<pixels {
                    let offset = pixel * 4
                    if max(bytes[offset], max(bytes[offset + 1], bytes[offset + 2])) > 12 {
                        litPixels += 1
                    }
                    if let reference {
                        let db = abs(Int(bytes[offset]) - Int(reference[offset]))
                        let dg = abs(Int(bytes[offset + 1]) - Int(reference[offset + 1]))
                        let dr = abs(Int(bytes[offset + 2]) - Int(reference[offset + 2]))
                        differenceTotal += db + dg + dr
                        if max(db, max(dg, dr)) > 12 { changedPixels += 1 }
                    }
                }
                if Double(litPixels) / Double(pixels) < 0.01 { blackFrames += 1 }
                if reference != nil {
                    let meanDifference = Double(differenceTotal) / Double(pixels * 3)
                    let changedRatio = Double(changedPixels) / Double(pixels)
                    if meanDifference > 3.0 && changedRatio > 0.01 { distinctFrames += 1 }
                } else {
                    reference = Array(UnsafeBufferPointer(start: bytes, count: pixels * 4))
                    distinctFrames = 1
                }
            }
            let result: [String: Any] = [
                "sampleCount": samples,
                "distinctFrameCount": distinctFrames,
                "blackFrameCount": blackFrames
            ]
            let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
            print(String(decoding: data, as: UTF8.self))
        } catch {
            fputs("video quality check failed: \(error)\n", stderr)
            exit(2)
        }
    }
}

enum QualityError: Error { case usage, invalidVideo, invalidFrame }
