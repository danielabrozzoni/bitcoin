#include <bench/bench.h>
#include <headerssync.h>
#include <test/util/setup_common.h>
#include <chainparams.h>
#include <validation.h>
#include <pow.h>

void FindProofOfWork(CBlockHeader& starting_header)
{
    while (!CheckProofOfWork(starting_header.GetHash(), starting_header.nBits, Params().GetConsensus())) {
        ++(starting_header.nNonce);
    }
}

void GenerateHeaders(std::vector<CBlockHeader>& headers,
        size_t count, const uint256& starting_hash, const int nVersion, int prev_time,
        const uint256& merkle_root, const uint32_t nBits)
{
    uint256 prev_hash = starting_hash;

    while (headers.size() < count) {
        headers.emplace_back();
        CBlockHeader& next_header = headers.back();;
        next_header.nVersion = nVersion;
        next_header.hashPrevBlock = prev_hash;
        next_header.hashMerkleRoot = merkle_root;
        next_header.nTime = prev_time+1;
        next_header.nBits = nBits;

        FindProofOfWork(next_header);
        prev_hash = next_header.GetHash();
        prev_time = next_header.nTime;
    }
    return;
}

static void ProcessNextHeadersPresyncBench(benchmark::Bench& bench) {
    int target_blocks = 15000;
    int chain_work = target_blocks * 2;

    auto testing_setup = MakeNoLogFileContext<const TestChain100Setup>(ChainType::REGTEST);

    const CBlockIndex* chain_start = WITH_LOCK(::cs_main, return testing_setup->m_node.chainman->m_blockman.GetAllBlockIndices()).back();
    std::vector<CBlockHeader> chain;
    GenerateHeaders(chain, target_blocks, chain_start->GetBlockHash(),
            chain_start->nVersion, chain_start->nTime,
            ArithToUint256(0), chain_start->nBits);

    bench.run([&] {
        std::vector<CBlockHeader> chain1 = chain;
        std::vector<CBlockHeader> chain2 = chain;
        HeadersSyncState* hss = new HeadersSyncState(0, Params().GetConsensus(), *chain_start, chain_work);
        auto result = hss->ProcessNextHeaders(chain1, true);
        assert(result.success);
        assert(hss->GetState() == HeadersSyncState::State::REDOWNLOAD);
        auto result2 = hss->ProcessNextHeaders(chain2, true);
        assert(result2.success);
        assert(hss->GetState() == HeadersSyncState::State::FINAL);
    });
}

BENCHMARK(ProcessNextHeadersPresyncBench, benchmark::PriorityLevel::HIGH);
